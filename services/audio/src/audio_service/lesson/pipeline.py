"""Pipeline tạo bài đầu-cuối: URL -> yt-dlp -> ffmpeg -> Demucs -> Whisper -> tách câu -> F0/PPG.

Tách thành các bước mà job runner (`jobs.py`) ghép lại (D-01):
`create_lesson` (ghi bài `queued`) -> `stage_download` (song song nhiều bài) ->
`stage_model` (một bài một lúc dưới cổng model). `run_lesson` chạy cả chuỗi một mạch cho smoke
script và test.

Mọi lần đổi trạng thái đều ghi `lesson.json` atomic để poller (card S1) đọc tiến độ miễn phí
(D-06). Ngoại lệ nào sau lần ghi đầu cũng để lại `status: "failed"` + `error {step, message}` với
message cố định (không chứa đường dẫn/ngoại lệ), rồi mới ném lại.

Các stage nặng được tiêm qua `PipelineDeps` (test dùng stage giả, không nạp model). Model nạp
tuần tự và giải phóng giữa các stage (máy 8 GB, Pitfall 10).
"""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from ulid import ULID
from yt_dlp.utils import DownloadError

from audio_service.config import (
    lesson_json_path,
    segment_features_path,
    video_asset_path,
)
from audio_service.contracts_gen import AudioQuality, Lesson, LessonError, Segment
from audio_service.lesson import audio_io, download, features, separate, store, transcribe
from audio_service.lesson.quality import audio_quality_label, non_vocal_ratio
from audio_service.lesson.segment import AsrWord, split_sentences
from audio_service.lesson.timing import StepTimer
from audio_service.lesson.urls import parse_youtube_url

logger = logging.getLogger(__name__)

PAD_MS = 150  # D-05
END_EXTRA_MS = 0  # D-05: "Mất chữ cuối?" chỉnh sau, P0 luôn 0
ERROR_MESSAGE_MAX = 500
DEFAULT_WHOLE_VIDEO_MAX_S = 360.0  # LES-02: <= 6 phút lấy cả video
DEFAULT_RANGE_LONG_S = 300.0  # video dài hơn: mặc định 0-5 phút

DOWNLOAD_BLOCKED_MESSAGE = "video bị giới hạn khu vực, riêng tư hoặc tắt tải xuống"
NO_SPEECH_MESSAGE = "không tìm thấy câu nói nào trong đoạn này. Hãy chọn đoạn khác hoặc video khác"
UNEXPECTED_ERROR_MESSAGE = "lỗi không mong đợi (xem log của make dev)"


@dataclass(frozen=True)
class PipelineDeps:
    """Các stage của pipeline. Bản thật ở `default_deps()`; test tiêm bản giả."""

    fetch_info: Callable[[str], download.VideoInfo]
    download_video: Callable[[str], Path]
    extract_audio: Callable[[Path, Path], None]
    separate: Callable[[np.ndarray, int], tuple[np.ndarray, np.ndarray]]
    transcribe: Callable[..., list[AsrWord]]  # (audio16k, *, offset_s)
    load_ppg: Callable[[], Any]
    compute_ppg: Callable[[np.ndarray, Any], np.ndarray]
    extract_f0: Callable[[np.ndarray], np.ndarray]
    frame_energy: Callable[[np.ndarray], np.ndarray]
    free_memory: Callable[[], None]


def _real_separate(stereo: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """Nạp Demucs, chạy, rồi giải phóng. MPS lỗi thì thử lại một lần trên CPU."""
    device = separate.pick_device()
    separator = separate.load_separator(device)
    try:
        try:
            return separate.separate_vocals(stereo, sr, separator)
        except RuntimeError:
            if device != "mps":
                raise
            logger.warning("Demucs trên MPS lỗi, thử lại trên CPU", exc_info=True)
            del separator
            separate.free_accelerator_memory()
            separator = separate.load_separator("cpu")
            return separate.separate_vocals(stereo, sr, separator)
    finally:
        del separator
        separate.free_accelerator_memory()


def default_deps() -> PipelineDeps:
    return PipelineDeps(
        fetch_info=download.fetch_info,
        download_video=download.download_video,
        extract_audio=audio_io.extract_audio,
        separate=_real_separate,
        transcribe=transcribe.transcribe_words,
        load_ppg=lambda: features.load_ppg_model(separate.pick_device()),
        compute_ppg=features.compute_ppg,
        extract_f0=features.extract_f0,
        frame_energy=features.frame_energy,
        free_memory=separate.free_accelerator_memory,
    )


@dataclass
class LessonRun:
    lesson: Lesson
    lesson_path: Path
    timings: dict[str, float]
    non_vocal_ratio: float


def build_segments(words: Sequence[AsrWord], spans: Sequence[tuple[int, int]]) -> list[Segment]:
    """Span nửa mở trên danh sách từ -> Segment của contract.

    `Word.i` chạy từ 0 trong từng segment (01-01 mục 4); mốc là giây từ đầu video (D-01);
    field tuỳ chọn bị bỏ hẳn, không truyền None (Pitfall 5).
    """
    segments: list[Segment] = []
    for index, (a, b) in enumerate(spans):
        chunk = words[a:b]
        if not chunk:
            raise ValueError("span rỗng")
        texts = [w.text.strip() for w in chunk]
        segments.append(
            Segment.model_validate(
                {
                    "index": index,
                    "text": " ".join(texts),
                    "start": chunk[0].start,
                    "end": chunk[-1].end,
                    "endExtraMs": END_EXTRA_MS,
                    "words": [
                        {
                            "i": i,
                            "text": texts[i],
                            "start": w.start,
                            "end": w.end,
                            "asrProb": w.probability,
                        }
                        for i, w in enumerate(chunk)
                    ],
                }
            )
        )
    return segments


def _now_iso() -> str:
    """Cùng dạng với JS `toISOString()` (Pitfall 7)."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class StepError(Exception):
    """Lỗi đã biết của một bước; `message` là câu tiếng Việt cố định, không chứa đường dẫn/stack."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def default_range(duration_sec: float) -> tuple[float, float]:
    """Khoảng mặc định (LES-02): video <= 6 phút lấy cả video, dài hơn lấy 0-5 phút."""
    if duration_sec <= DEFAULT_WHOLE_VIDEO_MAX_S:
        return 0.0, duration_sec
    return 0.0, DEFAULT_RANGE_LONG_S


def resolve_range(
    duration_sec: float, start: float | None, end: float | None, *, use_default: bool
) -> tuple[float, float]:
    """Khoảng (start, end) giây đã kẹp vào video. ValueError khi rỗng/ngược/ngoài video.

    `use_default=True` và cả hai đều vắng -> `default_range`; vắng một đầu -> đầu/cuối video.
    """
    if use_default and start is None and end is None:
        return default_range(duration_sec)
    range_start = 0.0 if start is None else float(start)
    range_end = duration_sec if end is None else min(float(end), duration_sec)
    if range_start < 0 or range_start >= range_end:
        raise ValueError(
            f"khoảng không hợp lệ: start={range_start}, end={range_end} "
            f"(video dài {duration_sec} s)"
        )
    return range_start, range_end


def create_lesson(
    url: str,
    *,
    start: float | None = None,
    end: float | None = None,
    deps: PipelineDeps,
    timer: StepTimer | None = None,
    info: download.VideoInfo | None = None,
) -> Lesson:
    """Parse URL, lấy metadata, kiểm khoảng, rồi ghi bài `queued`. Raise trước khi ghi gì.

    `info` cho phép gọi tay đã có metadata (router vừa gọi `fetch_info` để tính khoảng mặc định).
    """
    timer = timer or StepTimer()
    video_id = parse_youtube_url(url)
    if info is None:
        with timer.step("download"):
            info = deps.fetch_info(video_id)
    range_start, range_end = resolve_range(info.duration_sec, start, end, use_default=False)

    lesson_id = str(ULID())
    payload: dict[str, object] = {
        "id": lesson_id,
        "videoId": video_id,
        "title": info.title,
        "durationSec": info.duration_sec,
        "status": "queued",
        "range": {"start": range_start, "end": range_end},
        "padMs": PAD_MS,
        "segments": [],
        "createdAt": _now_iso(),
    }
    if info.thumbnail_url is not None:
        payload["thumbnailUrl"] = info.thumbnail_url
    lesson = Lesson.model_validate(payload)
    with timer.step("write"):
        store.save_lesson(lesson)
    return lesson


def _set_status(
    lesson_id: str,
    timer: StepTimer,
    on_status: Callable[[Lesson], None] | None,
    **update: Any,
) -> Lesson:
    """Cập nhật bài trên đĩa (atomic, dưới khoá bài) rồi mới báo `on_status`."""
    with timer.step("write"):
        lesson = store.update_lesson(lesson_id, lambda current: current.model_copy(update=update))
    if on_status is not None:
        on_status(lesson)
    return lesson


def mark_failed(
    lesson_id: str,
    exc: BaseException,
    *,
    on_status: Callable[[Lesson], None] | None = None,
) -> None:
    """Ghi `failed` + `error {step: status hiện tại, message cố định}`; idempotent.

    Chi tiết lỗi thật chỉ vào log (T-02-07): lesson.json không bao giờ có text ngoại lệ/đường dẫn.
    """
    if isinstance(exc, StepError):
        message = exc.message
        logger.error("bài %s lỗi ở một bước đã biết: %s", lesson_id, message)
    else:
        message = UNEXPECTED_ERROR_MESSAGE
        logger.error("bài %s lỗi không mong đợi", lesson_id, exc_info=exc)

    def fail(current: Lesson) -> Lesson:
        if current.status == "failed":
            return current  # stage đã tự ghi; không ghi đè `step`
        error = LessonError.model_validate(
            {"step": current.status, "message": message[:ERROR_MESSAGE_MAX]}
        )
        return current.model_copy(update={"status": "failed", "error": error})

    try:
        lesson = store.update_lesson(lesson_id, fail)
    except Exception:
        logger.exception("không ghi được trạng thái failed cho bài %s", lesson_id)
        return
    if on_status is not None:
        on_status(lesson)


def stage_download(
    lesson_id: str,
    *,
    deps: PipelineDeps,
    timer: StepTimer | None = None,
    on_status: Callable[[Lesson], None] | None = None,
) -> Lesson:
    """downloading -> (video.mp4 + audio.wav, cache theo videoId) -> queued (chờ cổng model)."""
    timer = timer or StepTimer()
    try:
        lesson = _set_status(lesson_id, timer, on_status, status="downloading")
        video_id = lesson.video_id
        video_path = video_asset_path(video_id, "video.mp4")
        audio_path = video_asset_path(video_id, "audio.wav")
        with timer.step("download"):
            if not video_path.exists():
                try:
                    deps.download_video(video_id)
                except DownloadError as exc:
                    raise StepError(DOWNLOAD_BLOCKED_MESSAGE) from exc
        with timer.step("extract_audio"):
            if not audio_path.exists():
                deps.extract_audio(video_path, audio_path)
        return _set_status(lesson_id, timer, on_status, status="queued")
    except BaseException as exc:
        mark_failed(lesson_id, exc, on_status=on_status)
        raise


def stage_model(
    lesson_id: str,
    *,
    deps: PipelineDeps,
    timer: StepTimer | None = None,
    on_status: Callable[[Lesson], None] | None = None,
) -> Lesson:
    """separating -> transcribing -> segmenting -> analyzing -> ready (cần giữ cổng model)."""
    timer = timer or StepTimer()
    try:
        return _run_model_stage(lesson_id, deps, timer, on_status)
    except BaseException as exc:
        mark_failed(lesson_id, exc, on_status=on_status)
        raise


def _run_model_stage(
    lesson_id: str,
    deps: PipelineDeps,
    timer: StepTimer,
    on_status: Callable[[Lesson], None] | None,
) -> Lesson:
    lesson = store.load_lesson(lesson_id)
    video_id = lesson.video_id
    range_start, range_end = lesson.range.start, lesson.range.end
    audio_path = video_asset_path(video_id, "audio.wav")
    vocals_path = video_asset_path(video_id, "vocals.wav")
    no_vocals_path = video_asset_path(video_id, "no_vocals.wav")

    # --- separating: trên TOÀN BỘ audio của video, cache theo videoId (D-07/D-08) ---
    _set_status(lesson_id, timer, on_status, status="separating")
    with timer.step("demucs"):
        if vocals_path.exists() and no_vocals_path.exists():
            vocals, sr = audio_io.read_audio(vocals_path)
            no_vocals, _ = audio_io.read_audio(no_vocals_path)
        else:
            stereo, sr = audio_io.read_audio(audio_path)
            vocals, no_vocals = deps.separate(stereo, sr)
            del stereo
            deps.free_memory()
            audio_io.write_audio(vocals_path, vocals, sr)
            audio_io.write_audio(no_vocals_path, no_vocals, sr)
    with timer.step("quality"):
        ratio = non_vocal_ratio(
            audio_io.slice_seconds(vocals, sr, range_start, range_end),
            audio_io.slice_seconds(no_vocals, sr, range_start, range_end),
        )
        quality = AudioQuality.model_validate(
            {"label": audio_quality_label(ratio), "nonVocalRatio": ratio}
        )
    del no_vocals

    # --- transcribing ---
    _set_status(lesson_id, timer, on_status, status="transcribing", audio_quality=quality)
    with timer.step("resample"):
        vocals16 = audio_io.to_mono_16k(vocals, sr)
        del vocals
    with timer.step("whisper"):
        words = deps.transcribe(
            audio_io.slice_seconds(vocals16, audio_io.TARGET_SR, range_start, range_end),
            offset_s=range_start,
        )
        deps.free_memory()  # giải phóng Whisper ngay sau bước của nó (D-18, Pitfall 2)

    # --- segmenting ---
    _set_status(lesson_id, timer, on_status, status="segmenting")
    with timer.step("segment"):
        segments = build_segments(words, split_sentences(words))
    if not segments:
        raise StepError(NO_SPEECH_MESSAGE)

    # --- analyzing: F0 + energy + PPG của bản gốc, cắt theo cửa sổ có đệm (D-05) ---
    seg_dir = segment_features_path(lesson_id, 0).parent
    shutil.rmtree(seg_dir, ignore_errors=True)  # .npz cũ của lần chạy trước (retry) sẽ mồ côi
    lesson = _set_status(lesson_id, timer, on_status, status="analyzing", segments=segments)
    with timer.step("ppg"):
        ppg_model = deps.load_ppg()
    try:
        for seg in segments:
            w_start, w_end = features.segment_window(
                seg.start,
                seg.end,
                lesson.pad_ms,
                seg.end_extra_ms,
                lo=0.0,
                hi=lesson.duration_sec,
            )
            clip = audio_io.slice_seconds(vocals16, audio_io.TARGET_SR, w_start, w_end)
            with timer.step("f0"):
                f0 = deps.extract_f0(clip)
                energy = deps.frame_energy(clip)
            with timer.step("ppg"):
                ppg = deps.compute_ppg(clip, ppg_model)
            with timer.step("write_features"):
                out = segment_features_path(lesson_id, seg.index)
                out.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    out,
                    f0_hz=f0,
                    energy=energy,
                    ppg=ppg,
                    window=np.array([w_start, w_end]),
                    sr=audio_io.TARGET_SR,
                    f0_hop_s=0.01,
                    ppg_fps=50.0,
                )
    finally:
        del ppg_model
        deps.free_memory()

    return _set_status(lesson_id, timer, on_status, status="ready")


def run_lesson(
    url: str,
    *,
    start: float | None = None,
    end: float | None = None,
    deps: PipelineDeps | None = None,
    timer: StepTimer | None = None,
    on_status: Callable[[Lesson], None] | None = None,
) -> LessonRun:
    """Chạy tuần tự cả hai stage trong một lời gọi (smoke script, test). Hành vi cũ được giữ.

    Stage tải đặt lại `queued` ở cuối (chờ cổng model); wrapper không báo trạng thái trùng đó để
    chuỗi `queued -> downloading -> separating ...` mà `on_status` thấy không đổi.
    """
    deps = deps or default_deps()
    timer = timer or StepTimer()

    last_reported: list[str] = []

    def report(lesson: Lesson) -> None:
        if lesson.status == "queued" and last_reported and last_reported[-1] == "downloading":
            last_reported.append("queued")
            return
        last_reported.append(lesson.status)
        if on_status is not None:
            on_status(lesson)

    lesson = create_lesson(url, start=start, end=end, deps=deps, timer=timer)
    report(lesson)
    stage_download(lesson.id, deps=deps, timer=timer, on_status=report)
    lesson = stage_model(lesson.id, deps=deps, timer=timer, on_status=report)

    ratio = lesson.audio_quality.non_vocal_ratio if lesson.audio_quality is not None else 0.0
    return LessonRun(
        lesson=lesson,
        lesson_path=lesson_json_path(lesson.id),
        timings=timer.timings,
        non_vocal_ratio=ratio,
    )

"""Pipeline tạo bài đầu-cuối: URL -> yt-dlp -> ffmpeg -> Demucs -> Whisper -> tách câu -> F0/PPG.

`run_lesson` ghi lại `lesson.json` (atomic) ở MỌI lần đổi trạng thái
queued -> downloading -> separating -> transcribing -> segmenting -> analyzing -> ready, để
poller (job runner Phase 2, card S1) đọc tiến độ miễn phí (D-06). Ngoại lệ nào sau lần ghi đầu
tiên cũng để lại `status: "failed"` + `error {step, message}` rồi mới ném lại.

Các stage nặng được tiêm qua `PipelineDeps` (test dùng stage giả, không nạp model). Model nạp
tuần tự và giải phóng giữa các stage (máy 8 GB, Pitfall 10).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from ulid import ULID

from audio_service.config import (
    lesson_json_path,
    segment_features_path,
    video_asset_path,
)
from audio_service.contract_io import write_contract_json
from audio_service.contracts_gen import AudioQuality, Lesson, LessonError, Segment
from audio_service.lesson import audio_io, download, features, separate, transcribe
from audio_service.lesson.quality import audio_quality_label, non_vocal_ratio
from audio_service.lesson.segment import AsrWord, split_sentences
from audio_service.lesson.timing import StepTimer
from audio_service.lesson.urls import parse_youtube_url

logger = logging.getLogger(__name__)

PAD_MS = 150  # D-05
END_EXTRA_MS = 0  # D-05: "Mất chữ cuối?" chỉnh sau, P0 luôn 0
ERROR_MESSAGE_MAX = 500


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


def run_lesson(
    url: str,
    *,
    start: float | None = None,
    end: float | None = None,
    deps: PipelineDeps | None = None,
    timer: StepTimer | None = None,
    on_status: Callable[[Lesson], None] | None = None,
) -> LessonRun:
    deps = deps or default_deps()
    timer = timer or StepTimer()

    video_id = parse_youtube_url(url)  # raise trước khi ghi bất cứ thứ gì
    lesson_id = str(ULID())
    path = lesson_json_path(lesson_id)

    with timer.step("download"):
        info = deps.fetch_info(video_id)
    range_start = 0.0 if start is None else float(start)
    range_end = info.duration_sec if end is None else min(float(end), info.duration_sec)
    if range_start < 0 or range_start >= range_end:
        raise ValueError(
            f"khoảng không hợp lệ: start={range_start}, end={range_end} "
            f"(video dài {info.duration_sec} s)"
        )

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

    def save(**update: Any) -> None:
        nonlocal lesson
        lesson = lesson.model_copy(update=update)
        with timer.step("write"):
            write_contract_json(path, lesson)
        if on_status is not None:
            on_status(lesson)

    ratio = 0.0
    try:
        with timer.step("write"):
            write_contract_json(path, lesson)
        if on_status is not None:
            on_status(lesson)

        # --- downloading (cả ffmpeg tách audio) ---
        save(status="downloading")
        with timer.step("download"):
            if not video_asset_path(video_id, "video.mp4").exists():
                deps.download_video(video_id)
        video_path = video_asset_path(video_id, "video.mp4")
        audio_path = video_asset_path(video_id, "audio.wav")
        vocals_path = video_asset_path(video_id, "vocals.wav")
        no_vocals_path = video_asset_path(video_id, "no_vocals.wav")
        with timer.step("extract_audio"):
            if not audio_path.exists():
                deps.extract_audio(video_path, audio_path)

        # --- separating: trên TOÀN BỘ audio của video, cache theo videoId (D-07/D-08) ---
        save(status="separating")
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
        lesson = lesson.model_copy(update={"audio_quality": quality})
        del no_vocals

        # --- transcribing ---
        save(status="transcribing")
        with timer.step("resample"):
            vocals16 = audio_io.to_mono_16k(vocals, sr)
            del vocals
        with timer.step("whisper"):
            words = deps.transcribe(
                audio_io.slice_seconds(vocals16, audio_io.TARGET_SR, range_start, range_end),
                offset_s=range_start,
            )
            deps.free_memory()

        # --- segmenting ---
        save(status="segmenting")
        with timer.step("segment"):
            segments = build_segments(words, split_sentences(words))
        if not segments:
            raise RuntimeError("NoSpeech: không nhận ra lời nói trong khoảng đã chọn")

        # --- analyzing: F0 + energy + PPG của bản gốc, cắt theo cửa sổ có đệm (D-05) ---
        save(status="analyzing", segments=segments)
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
                    hi=info.duration_sec,
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

        save(status="ready")
    except BaseException as exc:
        message = f"{type(exc).__name__}: {exc}"[:ERROR_MESSAGE_MAX]
        try:
            save(
                status="failed",
                error=LessonError.model_validate({"step": lesson.status, "message": message}),
            )
        except Exception:
            logger.exception("không ghi được trạng thái failed cho bài %s", lesson_id)
        raise

    return LessonRun(lesson=lesson, lesson_path=path, timings=timer.timings, non_vocal_ratio=ratio)

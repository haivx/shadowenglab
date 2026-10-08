"""Test pipeline tạo bài với stage giả: trạng thái, lỗi, cache, URL sai, chỉ số từ (D-05..D-07).

Không nạp model, không gọi mạng, không chạy ffmpeg: mọi stage nặng được tiêm qua PipelineDeps.
"""

from __future__ import annotations

import json
import math
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from audio_service import config
from audio_service.config import (
    get_settings,
    lesson_json_path,
    segment_features_path,
    stems_dir,
    video_asset_path,
)
from audio_service.contract_io import dump_contract
from audio_service.contracts_gen import Lesson
from audio_service.lesson import urls
from audio_service.lesson.audio_io import write_audio
from audio_service.lesson.download import VideoInfo
from audio_service.lesson.pipeline import (
    NO_SPEECH_MESSAGE,
    PAD_MS,
    UNEXPECTED_ERROR_MESSAGE,
    PipelineDeps,
    StepError,
    build_segments,
    create_lesson,
    load_range_vocals16,
    run_lesson,
    stage_download,
    stage_model,
)
from audio_service.lesson.segment import AsrWord
from audio_service.lesson.urls import InvalidYoutubeUrl

VIDEO_ID = "dUDi-F6eAvk"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
DURATION = 12.0
SR = 44100
STATUSES = [
    "queued",
    "downloading",
    "separating",
    "transcribing",
    "segmenting",
    "analyzing",
    "ready",
]


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


# Hai câu rõ ràng (kết thúc bằng dấu câu), mỗi câu >= 3 s (MIN_DUR_S, D-21) để split_sentences
# cho đúng 2 segment.
_WORDS = [
    (" Hello", 0.5, 1.1, 0.9),
    (" there,", 1.2, 1.9, 0.8),
    (" my", 2.0, 2.4, 0.95),
    (" friend.", 2.5, 3.8, 0.7),
    (" How", 4.4, 4.8, 0.9),
    (" are", 4.9, 5.3, 0.85),
    (" you", 5.4, 5.8, 0.99),
    (" today?", 5.9, 7.6, 0.6),
]


class Fakes:
    """Stage giả + sổ ghi lời gọi."""

    def __init__(
        self,
        *,
        transcribe_error: Exception | None = None,
        words: list[tuple[str, float, float, float]] | None = None,
        thumbnail: str | None = None,
        duration: float = DURATION,
        vocab_error: Exception | None = None,
        ramp: bool = False,
    ) -> None:
        self.calls: list[str] = []
        self.transcribe_args: list[tuple[int, float]] = []
        self.transcribe_first_sample: list[float] = []
        self.separate_samples: list[int] = []
        self.f0_clip_lengths: list[int] = []
        self.ramp = ramp
        self.transcribe_error = transcribe_error
        self.words = _WORDS if words is None else words
        self.thumbnail = thumbnail
        self.duration = duration
        self.vocab_error = vocab_error

    def deps(self) -> PipelineDeps:
        return PipelineDeps(
            fetch_info=self.fetch_info,
            download_video=self.download_video,
            extract_audio=self.extract_audio,
            separate=self.separate,
            transcribe=self.transcribe,
            load_ppg=self.load_ppg,
            compute_ppg=self.compute_ppg,
            extract_f0=self.extract_f0,
            frame_energy=self.frame_energy,
            free_memory=lambda: self.calls.append("free_memory"),
            load_vocab=self.load_vocab,
        )

    def fetch_info(self, video_id: str) -> VideoInfo:
        self.calls.append("fetch_info")
        return VideoInfo(video_id, "Fake title", self.duration, self.thumbnail)

    def download_video(self, video_id: str) -> Path:
        self.calls.append("download_video")
        path = video_asset_path(video_id, "video.mp4")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a real video")
        return path

    def extract_audio(self, video_path: Path, wav_path: Path) -> None:
        self.calls.append("extract_audio")
        t = np.arange(int(SR * self.duration)) / SR
        if self.ramp:  # mẫu = t / 100: biết được lát cắt bắt đầu từ giây nào
            tone = (t / 100.0).astype(np.float32)
        else:
            tone = (0.3 * np.sin(2 * math.pi * 220.0 * t)).astype(np.float32)
        write_audio(wav_path, np.stack([tone, tone]), SR)

    def separate(self, stereo: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
        self.calls.append("separate")
        assert stereo.ndim == 2 and stereo.shape[0] == 2 and sr == SR
        self.separate_samples.append(stereo.shape[1])
        return (0.9 * stereo).astype(np.float32), (0.1 * stereo).astype(np.float32)

    def transcribe(self, audio16k: np.ndarray, *, offset_s: float) -> list[AsrWord]:
        self.calls.append("transcribe")
        self.transcribe_args.append((len(audio16k), offset_s))
        self.transcribe_first_sample.append(float(audio16k[0]))
        if self.transcribe_error is not None:
            raise self.transcribe_error
        return [AsrWord(t, s + offset_s, e + offset_s, p) for t, s, e, p in self.words]

    def load_ppg(self) -> object:
        self.calls.append("load_ppg")
        return object()

    def load_vocab(self) -> dict[int, str]:
        self.calls.append("load_vocab")
        if self.vocab_error is not None:
            raise self.vocab_error
        return {0: "<pad>", 1: "<s>", 2: "</s>", 3: "<unk>", 4: "h"}

    def compute_ppg(self, clip: np.ndarray, _model: object) -> np.ndarray:
        """Toàn blank, một đỉnh tự tin ở frame 15: rơi vào từ 0 của mỗi câu (không vào từ 1)."""
        ppg = np.zeros((max(len(clip) // 320, 1), 5), dtype=np.float32)
        ppg[:, 0] = 1.0
        if ppg.shape[0] > 15:
            ppg[15] = [0.02, 0.02, 0.02, 0.02, 0.92]
        return ppg

    def extract_f0(self, clip: np.ndarray) -> np.ndarray:
        self.f0_clip_lengths.append(len(clip))
        return np.zeros(max(len(clip) // 160, 1), dtype=np.float32)

    def frame_energy(self, clip: np.ndarray) -> np.ndarray:
        return np.zeros(max(len(clip) // 160, 1), dtype=np.float32)


def _only_lesson_id(data_dir: Path) -> str:
    dirs = [p for p in (data_dir / "lessons").iterdir() if p.is_dir()]
    assert len(dirs) == 1
    return dirs[0].name


# --- trạng thái -----------------------------------------------------------------------------


def test_statuses_follow_the_order_and_each_is_on_disk_when_reported(data_dir: Path) -> None:
    fakes = Fakes()
    seen: list[str] = []

    def on_status(lesson: Lesson) -> None:
        on_disk = json.loads(lesson_json_path(lesson.id).read_text(encoding="utf-8"))
        assert on_disk["status"] == lesson.status  # đã ghi atomic trước khi báo
        seen.append(lesson.status)

    run = run_lesson(URL, deps=fakes.deps(), on_status=on_status)

    assert seen == STATUSES
    assert run.lesson.status == "ready"
    assert run.lesson_path == lesson_json_path(run.lesson.id)
    assert {"download", "demucs", "whisper", "segment", "f0", "ppg"} <= set(run.timings)


def test_final_lesson_validates_and_carries_pad_and_explicit_zero_end_extra(
    data_dir: Path,
) -> None:
    run = run_lesson(URL, deps=Fakes(thumbnail="https://i.example/t.jpg").deps())

    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    lesson = Lesson.model_validate_json(run.lesson_path.read_text(encoding="utf-8"))

    assert lesson.status == "ready"
    assert raw["padMs"] == PAD_MS == 150
    assert raw["videoId"] == VIDEO_ID
    assert raw["range"] == {"start": 0.0, "end": DURATION}
    assert raw["thumbnailUrl"] == "https://i.example/t.jpg"
    assert raw["createdAt"].endswith("Z") and "+00:00" not in raw["createdAt"]
    assert len(raw["segments"]) == 2
    assert all(seg["endExtraMs"] == 0 for seg in raw["segments"])  # tường minh, không phải mặc định
    assert "error" not in raw


def test_thumbnail_is_omitted_not_null_when_unknown(data_dir: Path) -> None:
    run = run_lesson(URL, deps=Fakes(thumbnail=None).deps())

    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    assert "thumbnailUrl" not in raw
    assert "error" not in raw


def test_audio_quality_label_is_written_from_the_stems(data_dir: Path) -> None:
    run = run_lesson(URL, deps=Fakes().deps())

    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    # no_vocals = 0.1 * x, vocals = 0.9 * x -> power ratio (0.1 / 0.9) ** 2 ~ 0.0123 (< 0.0316)
    assert raw["audioQuality"]["label"] == "clean"
    assert raw["audioQuality"]["nonVocalRatio"] == pytest.approx((0.1 / 0.9) ** 2, rel=1e-3)
    assert run.non_vocal_ratio == pytest.approx((0.1 / 0.9) ** 2, rel=1e-3)


def test_word_index_restarts_at_zero_in_every_segment(data_dir: Path) -> None:
    run = run_lesson(URL, deps=Fakes().deps())

    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    for seg in raw["segments"]:
        assert [w["i"] for w in seg["words"]] == list(range(len(seg["words"])))
    assert [seg["text"] for seg in raw["segments"]] == [
        "Hello there, my friend.",
        "How are you today?",
    ]
    assert raw["segments"][1]["words"][0]["text"] == "How"  # đã strip khoảng trắng của Whisper
    assert raw["segments"][1]["start"] == 4.4
    assert raw["segments"][1]["end"] == 7.6


def test_one_npz_per_segment_with_expected_keys_and_padded_window(data_dir: Path) -> None:
    run = run_lesson(URL, deps=Fakes().deps())

    assert len(run.lesson.segments) == 2
    for seg in run.lesson.segments:
        path = segment_features_path(run.lesson.id, seg.index)
        with np.load(path) as npz:
            assert {"f0_hz", "energy", "ppg", "window"} <= set(npz.files)
            lo, hi = (float(x) for x in npz["window"])
            assert lo == pytest.approx(max(0.0, seg.start - 0.15))
            assert hi == pytest.approx(min(DURATION, seg.end + 0.15))
            assert npz["ppg"].dtype == np.float32
            assert float(npz["f0_hop_s"]) == 0.01
            assert float(npz["ppg_fps"]) == 50.0
    assert not segment_features_path(run.lesson.id, 2).exists()


def test_confident_words_get_ipa_from_the_ppg_and_the_rest_have_no_key(data_dir: Path) -> None:
    run = run_lesson(URL, deps=Fakes().deps())

    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    for seg in raw["segments"]:
        assert seg["words"][0]["ipa"] == "h"
        assert all("ipa" not in word for word in seg["words"][1:])  # vắng mặt, không phải null
    assert "null" not in run.lesson_path.read_text(encoding="utf-8")
    Lesson.model_validate(raw)


def test_missing_vocab_degrades_to_no_ipa_without_failing_the_lesson(data_dir: Path) -> None:
    fakes = Fakes(vocab_error=FileNotFoundError("vocab.json not cached"))

    run = run_lesson(URL, deps=fakes.deps())

    assert run.lesson.status == "ready"
    raw = json.loads(run.lesson_path.read_text(encoding="utf-8"))
    assert all("ipa" not in word for seg in raw["segments"] for word in seg["words"])


def test_range_offsets_the_words_and_limits_the_whisper_input(data_dir: Path) -> None:
    fakes = Fakes()

    run = run_lesson(URL, start=2.0, end=8.0, deps=fakes.deps())

    assert run.lesson.range.start == 2.0 and run.lesson.range.end == 8.0
    ((n_samples, offset),) = fakes.transcribe_args
    assert offset == 2.0
    assert n_samples == 6 * 16000  # đúng lát 6 s ở 16 kHz
    first = run.lesson.segments[0]
    assert first.start == pytest.approx(2.5)  # mốc giây từ đầu VIDEO (D-01)


def test_end_beyond_the_video_is_clamped_to_its_duration(data_dir: Path) -> None:
    run = run_lesson(URL, start=1.0, end=999.0, deps=Fakes().deps())

    assert run.lesson.range.end == DURATION


# --- lỗi ------------------------------------------------------------------------------------


def test_failure_leaves_failed_status_with_step_and_message_then_reraises(data_dir: Path) -> None:
    fakes = Fakes(transcribe_error=RuntimeError("boom"))
    seen: list[str] = []

    with pytest.raises(RuntimeError, match="boom"):
        run_lesson(URL, deps=fakes.deps(), on_status=lambda lesson: seen.append(lesson.status))

    lesson_id = _only_lesson_id(data_dir)
    raw = json.loads(lesson_json_path(lesson_id).read_text(encoding="utf-8"))
    assert raw["status"] == "failed"
    # Message cố định, không lộ text ngoại lệ (T-02-07).
    assert raw["error"] == {"step": "transcribing", "message": UNEXPECTED_ERROR_MESSAGE}
    Lesson.model_validate(raw)  # file vẫn là contract hợp lệ
    assert seen == ["queued", "downloading", "separating", "transcribing", "failed"]
    assert not list((data_dir / "lessons" / lesson_id).glob("*.tmp"))


def test_exception_text_and_paths_never_reach_lesson_json(data_dir: Path) -> None:
    fakes = Fakes(transcribe_error=RuntimeError("x" * 5000 + f" {data_dir}/secret"))

    with pytest.raises(RuntimeError):
        run_lesson(URL, deps=fakes.deps())

    text = lesson_json_path(_only_lesson_id(data_dir)).read_text(encoding="utf-8")
    assert "xxxx" not in text and str(data_dir) not in text and "secret" not in text


def test_no_speech_fails_at_segmenting_instead_of_an_empty_ready_lesson(data_dir: Path) -> None:
    fakes = Fakes(words=[])

    with pytest.raises(StepError):
        run_lesson(URL, deps=fakes.deps())

    raw = json.loads(lesson_json_path(_only_lesson_id(data_dir)).read_text(encoding="utf-8"))
    assert raw["status"] == "failed"
    assert raw["error"] == {"step": "segmenting", "message": NO_SPEECH_MESSAGE}


def test_failure_in_an_early_stage_reports_the_current_status(data_dir: Path) -> None:
    fakes = Fakes()

    def broken_download(video_id: str) -> Path:
        raise ConnectionError("network down")

    deps = fakes.deps()
    deps = PipelineDeps(**{**deps.__dict__, "download_video": broken_download})

    with pytest.raises(ConnectionError):
        run_lesson(URL, deps=deps)

    raw = json.loads(lesson_json_path(_only_lesson_id(data_dir)).read_text(encoding="utf-8"))
    assert raw["status"] == "failed"
    assert raw["error"]["step"] == "downloading"


# --- cache (D-07) ---------------------------------------------------------------------------


def _stem_files(start_ms: int, end_ms: int) -> tuple[Path, Path]:
    folder = stems_dir(VIDEO_ID, start_ms, end_ms)
    return folder / "vocals.wav", folder / "no_vocals.wav"


def test_second_run_reuses_video_audio_and_stems(data_dir: Path) -> None:
    first = Fakes()
    run1 = run_lesson(URL, deps=first.deps())
    assert {"download_video", "extract_audio", "separate"} <= set(first.calls)
    for asset in ("video.mp4", "audio.wav"):
        assert video_asset_path(VIDEO_ID, asset).exists()  # type: ignore[arg-type]
    for stem in _stem_files(0, 12000):
        assert stem.exists()

    second = Fakes()
    run2 = run_lesson(URL, deps=second.deps())

    assert "download_video" not in second.calls
    assert "extract_audio" not in second.calls
    assert "separate" not in second.calls
    assert run2.lesson.status == "ready"
    assert run2.lesson.id != run1.lesson.id  # nhiều bài trên một video (D-07)
    assert [s.text for s in run2.lesson.segments] == [s.text for s in run1.lesson.segments]
    assert run2.non_vocal_ratio == pytest.approx(run1.non_vocal_ratio, rel=1e-4)


def test_partial_cache_without_stems_still_separates(data_dir: Path) -> None:
    first = Fakes()
    run_lesson(URL, deps=first.deps())
    _stem_files(0, 12000)[1].unlink()

    second = Fakes()
    run_lesson(URL, deps=second.deps())

    assert "separate" in second.calls
    assert "download_video" not in second.calls
    assert "extract_audio" not in second.calls


class _SlowExtractFakes(Fakes):
    """extract_audio chậm để hai bài cùng video chắc chắn chồng lên nhau nếu không có khoá."""

    def extract_audio(self, video_path: Path, wav_path: Path) -> None:
        time.sleep(0.2)
        super().extract_audio(video_path, wav_path)


def test_two_lessons_of_one_video_extract_the_audio_once(data_dir: Path) -> None:
    # Phát hiện ở `make smoke-jobs` (02-19): hai bài cùng video tải song song; bài thứ hai thoát
    # khoá tải ngay khi bài đầu tải xong, rồi cả hai cùng chạy ffmpeg ghi chung `audio.wav.part`
    # và bài chậm hơn lỗi FileNotFoundError ở os.replace.
    fakes = _SlowExtractFakes()
    deps = fakes.deps()
    lesson_ids = [create_lesson(URL, start=0, end=6, deps=deps).id for _ in range(2)]
    start = threading.Barrier(2)
    errors: list[BaseException] = []

    def run(lesson_id: str) -> None:
        start.wait()
        try:
            stage_download(lesson_id, deps=deps)
        except BaseException as exc:  # noqa: BLE001 - thu mọi lỗi để assert ở thread chính
            errors.append(exc)

    threads = [threading.Thread(target=run, args=(lesson_id,)) for lesson_id in lesson_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert fakes.calls.count("extract_audio") == 1
    for lesson_id in lesson_ids:
        raw = json.loads(lesson_json_path(lesson_id).read_text(encoding="utf-8"))
        assert raw["status"] == "queued"


# --- tách giọng theo đoạn đã chọn (D-19, LES-02) ---------------------------------------------


def test_separation_input_is_the_range_plus_one_second_each_side(data_dir: Path) -> None:
    fakes = Fakes()

    run_lesson(URL, start=4.0, end=8.0, deps=fakes.deps())

    assert fakes.separate_samples == [6 * SR]  # [3, 9) s thay vì cả video 12 s


def test_separation_margin_is_clamped_to_the_video(data_dir: Path) -> None:
    fakes = Fakes()

    run_lesson(URL, start=0.5, end=11.5, deps=fakes.deps())

    assert fakes.separate_samples == [12 * SR]  # [0, 12) kẹp trong video


def test_stems_are_cached_per_range_and_reused_only_for_the_same_range(data_dir: Path) -> None:
    first = Fakes()
    run_lesson(URL, start=4.0, end=8.0, deps=first.deps())
    for stem in _stem_files(4000, 8000):
        assert stem.exists()
    assert not _stem_files(0, 12000)[0].exists()  # không còn stem cả video

    same = Fakes()
    run_lesson(URL, start=4.0, end=8.0, deps=same.deps())
    assert same.separate_samples == []  # dùng lại cache

    different = Fakes()
    run_lesson(URL, start=2.0, end=8.0, deps=different.deps())
    assert different.separate_samples == [8 * SR]  # [1, 9) s: tách lại cho khoảng khác
    for stem in _stem_files(2000, 8000):
        assert stem.exists()
    for stem in _stem_files(4000, 8000):
        assert stem.exists()  # cache cũ không bị trộn hay xoá


def test_transcribe_gets_the_range_slice_and_windows_stay_absolute(data_dir: Path) -> None:
    fakes = Fakes(ramp=True)

    run = run_lesson(URL, start=4.0, end=8.0, deps=fakes.deps())

    ((n_samples, offset),) = fakes.transcribe_args
    assert n_samples == 4 * 16000
    assert offset == 4.0
    # mẫu = 0.9 * t / 100 (vocals = 0.9 * x): lát cắt phải bắt đầu đúng giây 4.0 của video
    assert fakes.transcribe_first_sample[0] == pytest.approx(0.9 * 4.0 / 100.0, abs=1e-4)
    first = run.lesson.segments[0]
    assert first.start == pytest.approx(4.5)  # mốc tuyệt đối theo video (D-01)
    with np.load(segment_features_path(run.lesson.id, 0)) as npz:
        lo, hi = (float(x) for x in npz["window"])
    assert lo == pytest.approx(first.start - 0.15)
    assert hi == pytest.approx(first.end + 0.15)
    assert fakes.f0_clip_lengths[0] == pytest.approx((hi - lo) * 16000, abs=2)


def test_entering_analyzing_removes_stale_segment_features(data_dir: Path) -> None:
    fakes = Fakes()
    deps = fakes.deps()
    lesson = create_lesson(URL, deps=deps)
    stage_download(lesson.id, deps=deps)
    stale = segment_features_path(lesson.id, 9)
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"orphan from an earlier run")

    done = stage_model(lesson.id, deps=deps)

    assert len(done.segments) == 2
    assert not stale.exists()
    assert sorted(p.name for p in stale.parent.glob("*.npz")) == ["0000.npz", "0001.npz"]


def test_load_range_vocals16_returns_the_cached_stem_and_its_base_offset(data_dir: Path) -> None:
    fakes = Fakes(ramp=True)
    run = run_lesson(URL, start=4.0, end=8.0, deps=fakes.deps())

    vocals16, base_offset = load_range_vocals16(run.lesson)

    assert base_offset == 3.0
    assert vocals16.ndim == 1 and vocals16.dtype == np.float32
    assert len(vocals16) == 6 * 16000
    assert float(vocals16[16000]) == pytest.approx(0.9 * 4.0 / 100.0, abs=1e-4)  # giây 4.0


def test_load_range_vocals16_without_stems_raises_a_clear_error(data_dir: Path) -> None:
    run = run_lesson(URL, start=4.0, end=8.0, deps=Fakes().deps())
    for stem in _stem_files(4000, 8000):
        stem.unlink()

    with pytest.raises(StepError, match="giọng"):
        load_range_vocals16(run.lesson)


# --- đầu vào sai ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/watch?v=dUDi-F6eAvk",
        "file:///etc/passwd",
        "https://www.youtube.com/watch?v=short",
        "",
    ],
)
def test_invalid_url_raises_and_creates_nothing(data_dir: Path, url: str) -> None:
    fakes = Fakes()

    with pytest.raises(InvalidYoutubeUrl):
        run_lesson(url, deps=fakes.deps())

    assert fakes.calls == []
    assert not (data_dir / "lessons").exists()
    assert not (data_dir / "videos").exists()


@pytest.mark.parametrize(("start", "end"), [(5.0, 5.0), (8.0, 2.0), (-1.0, 4.0), (20.0, None)])
def test_bad_range_raises_before_writing_a_lesson(
    data_dir: Path, start: float, end: float | None
) -> None:
    with pytest.raises(ValueError, match="khoảng"):
        run_lesson(URL, start=start, end=end, deps=Fakes().deps())

    assert not (data_dir / "lessons").exists()


# --- build_segments -------------------------------------------------------------------------


def test_build_segments_numbers_words_from_zero_per_segment_and_omits_optionals() -> None:
    words = [
        AsrWord(" One.", 0.0, 0.5, 0.9),
        AsrWord(" Two", 1.0, 1.4, 0.8),
        AsrWord(" three", 1.5, 2.0, 0.7),
    ]

    segments = build_segments(words, [(0, 1), (1, 3)])

    assert [s.index for s in segments] == [0, 1]
    assert [[w.i for w in s.words] for s in segments] == [[0], [0, 1]]
    assert segments[1].text == "Two three"
    assert (segments[1].start, segments[1].end) == (1.0, 2.0)
    dumped = dump_contract(segments[1])
    assert dumped["endExtraMs"] == 0
    assert "translation" not in dumped
    word = dumped["words"][0]  # type: ignore[index]
    assert set(word) == {"i", "text", "start", "end", "asrProb"}  # không ipa/prominence/null


def test_real_separate_keeps_the_real_error_when_the_cpu_fallback_fails_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from audio_service.lesson import pipeline, separate

    monkeypatch.setattr(separate, "pick_device", lambda: "mps")

    def load(device: str) -> object:
        if device == "cpu":
            raise OSError("không nạp được model CPU")
        return object()

    def fail(*_a: object) -> None:
        raise RuntimeError("MPS hỏng")

    monkeypatch.setattr(separate, "load_separator", load)
    monkeypatch.setattr(separate, "separate_vocals", fail)
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: None)
    with pytest.raises(OSError, match="CPU"):
        pipeline._real_separate(np.zeros((2, 8), dtype=np.float32), 44100)


def test_build_segments_rejects_an_empty_span() -> None:
    with pytest.raises(ValueError):
        build_segments([AsrWord(" a", 0.0, 1.0, 0.5)], [(0, 0)])


# --- hai regex id video phải khớp nhau ------------------------------------------------------


@pytest.mark.parametrize(
    ("sample", "valid"),
    [
        ("dUDi-F6eAvk", True),
        ("-abcdefghij", True),
        ("___________", True),
        ("A1b2C3d4E5f", True),
        ("abcdefghij", False),  # 10 ký tự
        ("abcdefghijkl", False),  # 12 ký tự
        ("abcdefghij!", False),
        ("abc def ghi", False),
        ("abcdefghijk\n", False),
        ("../../etc/p", False),
        ("", False),
    ],
)
def test_video_id_regexes_in_config_and_urls_agree(sample: str, valid: bool) -> None:
    assert bool(config.VIDEO_ID_RE.fullmatch(sample)) is valid
    assert bool(urls.VIDEO_ID_RE.fullmatch(sample)) is valid

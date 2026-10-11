"""Tìm bài và clip, kiểm D-05, chấm lại WAV đã lưu bằng scorer hiện tại (04-02, D-05, D-06).

Chỉ đọc DATA_DIR (T-04-04): ref lấy bằng `ref_prosody_for_segment(..., write_cache=False)`,
đường dẫn clip dựng từ `config.data_root()` mà KHÔNG gọi `config.eval_clips_dir()` (hàm đó
`mkdir`). Không HTTP, không SQLite, không đọc `result_json` cũ: điểm và issue luôn tính lại từ WAV
(D-06).

Nạp feature (`load_clip`) tách khỏi chấm (`score_clip`) để sweep (04-03) tính feature một lần rồi
chấm nhiều lần với aligner nhớ đệm mà không sửa file này.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from audio_service import config
from audio_service.config import InvalidIdError
from audio_service.contracts_gen import EvalCase, Lesson
from audio_service.lesson import audio_io, pipeline, store, vad
from audio_service.scoring.align import Aligner, align
from audio_service.scoring.features import ProsodyFeatures, prepare_features
from audio_service.scoring.scorer import ProsodyScore, score_prosody
from evalkit.cases import stamp_mismatch

# `{lessonId}_{NNNN}_{AA}` do `routers/attempts._store_eval_clip` ghi (ULID 26 ký tự).
CLIP_STEM_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}_[0-9]{4}_[0-9]{2,}$")

# Feature bản gốc tính một lần mỗi câu: khoá (lessonId, segmentIndex).
RefCache = dict[tuple[str, int], pipeline.RefProsody]


class DataError(Exception):
    """Dữ liệu trên đĩa không khớp case (bài, clip, sidecar, dấu nhận diện); thoát 2."""


@dataclass(frozen=True)
class ClipInput:
    """Mọi thứ cần để chấm một clip: feature người học (None = không có tiếng) và bản gốc."""

    case: EvalCase
    ref: pipeline.RefProsody
    user: ProsodyFeatures | None
    words: list[str]


def clips_root() -> Path:
    """`DATA_DIR/eval_clips`, KHÔNG tạo thư mục (khác `config.eval_clips_dir()`)."""
    return config.data_root() / "eval_clips"


def load_lessons(cases: Sequence[EvalCase]) -> dict[str, Lesson]:
    """Bài của các case: phải đọc được, `ready`, và segmentIndex nằm trong bài (D-05)."""
    lessons: dict[str, Lesson] = {}
    for case in cases:
        lesson = lessons.get(case.lesson_id)
        if lesson is None:
            try:
                lesson = store.load_lesson(case.lesson_id)
            except (InvalidIdError, OSError, ValueError):
                raise DataError(
                    f"{case.case_id}: không đọc được bài {case.lesson_id} trong DATA_DIR "
                    "(bài bị xoá? D-05)"
                ) from None
            if lesson.status != "ready":
                raise DataError(
                    f"{case.case_id}: bài {case.lesson_id} chưa ở trạng thái ready "
                    f"(đang {lesson.status}) (D-05)"
                )
            lessons[case.lesson_id] = lesson
        if case.segment_index >= len(lesson.segments):
            raise DataError(
                f"{case.case_id}: bài {case.lesson_id} không có câu {case.segment_index} (D-05)"
            )
    return lessons


def check_identity(cases: Sequence[EvalCase], lessons: dict[str, Lesson]) -> None:
    """Dấu nhận diện câu phải khớp câu hiện tại; wordIndex phải nằm trong câu (D-05, A5, A6)."""
    for case in cases:
        segment = lessons[case.lesson_id].segments[case.segment_index]
        mismatch = stamp_mismatch(case, segment)
        if mismatch is not None:
            raise DataError(
                f"{case.case_id}: câu {case.lesson_id}#{case.segment_index} đã đổi so với lúc "
                f"viết case ({mismatch}) (D-05)"
            )
        if case.word_index is not None and case.word_index >= len(segment.words):
            raise DataError(
                f"{case.case_id}: wordIndex {case.word_index} ngoài câu ({len(segment.words)} từ)"
            )


def _read_sidecar(path: Path, case: EvalCase, stem: str) -> None:
    try:
        sidecar = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise DataError(f"{case.case_id}: thiếu hoặc hỏng sidecar của clip {stem}") from None
    if (
        not isinstance(sidecar, dict)
        or sidecar.get("lessonId") != case.lesson_id
        or sidecar.get("segmentIndex") != case.segment_index
    ):
        raise DataError(f"{case.case_id}: sidecar của clip {stem} không khớp bài/câu của case")


def load_clip(
    case: EvalCase,
    lesson: Lesson,
    root: Path,
    ref_cache: RefCache,
) -> ClipInput:
    """Nạp WAV đã lưu của `case.clip` và feature bản gốc của câu (một lần mỗi câu qua `ref_cache`).

    Stem đi vào đường dẫn nên qua `CLIP_STEM_RE` và kiểm đường dẫn đã resolve nằm trong `root`
    (T-04-03). WAV đã được chuẩn hoá 16 kHz mono lúc lưu; chỉ đọc lại, không chuẩn hoá lần nữa.
    """
    stem = case.clip
    if stem is None or not CLIP_STEM_RE.fullmatch(stem):
        raise DataError(f"{case.case_id}: tên clip {stem!r} không đúng dạng <lessonId>_<NNNN>_<AA>")
    if not stem.startswith(f"{case.lesson_id}_{case.segment_index:04d}_"):
        raise DataError(f"{case.case_id}: clip {stem} không thuộc bài/câu của case")
    base = root.resolve()
    wav = (root / f"{stem}.wav").resolve()
    sidecar = (root / f"{stem}.json").resolve()
    if not (wav.is_relative_to(base) and sidecar.is_relative_to(base)):
        raise DataError(f"{case.case_id}: clip {stem} thoát khỏi eval_clips")
    if not wav.is_file():
        raise DataError(f"{case.case_id}: thiếu WAV của clip {stem}")
    _read_sidecar(sidecar, case, stem)

    try:
        audio, sample_rate = audio_io.read_audio(wav)
    except (OSError, sf.LibsndfileError):
        raise DataError(f"{case.case_id}: không đọc được WAV của clip {stem}") from None
    mono = audio_io.to_mono_16k(audio, sample_rate)
    user = prepare_features(mono) if vad.is_voiced(mono) else None

    key = (lesson.id, case.segment_index)
    ref = ref_cache.get(key)
    if ref is None:
        try:
            ref = pipeline.ref_prosody_for_segment(lesson, case.segment_index, write_cache=False)
        except pipeline.StepError as exc:  # gồm RefAudioMissing
            raise DataError(f"{case.case_id}: {exc.message}") from None
        ref_cache[key] = ref
    return ClipInput(case=case, ref=ref, user=user, words=[word.text for word in ref.words])


def score_clip(clip: ClipInput, *, aligner: Aligner = align) -> ProsodyScore | None:
    """Chấm clip với ngưỡng hiện tại; None khi clip không có tiếng (VAD) nên không có gì để chấm."""
    if clip.user is None:
        return None
    return score_prosody(clip.ref.features, clip.user, clip.ref.words, aligner=aligner)

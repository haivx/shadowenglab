"""Sửa câu (PLY-04, D-16) và "Mất chữ cuối?" (PLY-05, D-14) trên `lesson.json`.

Phần thuần (`normalize_text`, `apply_text_edit`, `merge_ipa`) không đụng đĩa; mọi lần ghi đều qua
`store.update_lesson` (khoá riêng của bài, đọc-sửa-ghi) để PATCH / extend-end / translate cùng lúc
không làm mất ghi của nhau. Tính lại feature nặng nên KHÔNG giữ khoá bài: chỉ giữ cổng model.
"""

from __future__ import annotations

import logging
import unicodedata
from collections.abc import Mapping
from typing import Protocol

from audio_service.contracts_gen import Lesson, Segment
from audio_service.lesson import pipeline, store
from audio_service.lesson.jobs import InvalidState
from audio_service.lesson.timing import StepTimer

logger = logging.getLogger(__name__)

TEXT_MAX_CHARS = 500  # 02-01 mục A9: 1-500 ký tự sau khi trim, đếm theo code point NFC
EXTEND_STEP_MS = 300  # 02-01 mục E: mỗi lần bấm "Mất chữ cuối?" nới thêm 300 ms
# Giả định do planner đề xuất (không có trong CONTEXT), báo Liam ở SUMMARY / PR: đổi bằng 1 hằng số.
EXTEND_MAX_MS = 3000
RECOMPUTE_TIMEOUT_S = 150.0  # 02-01 mục E: chờ cổng model tối đa 150 s rồi trả 503 busy


class _Gate(Protocol):
    """Phần của `threading.Lock` mà `recompute_segment` dùng (test tiêm khoá thật)."""

    def acquire(self, blocking: bool = ..., timeout: float = ...) -> bool: ...

    def release(self) -> None: ...


class ExtendLimit(InvalidState):
    """`endExtraMs` đã chạm trần `EXTEND_MAX_MS` (HTTP 409 invalid_state)."""


class Busy(Exception):
    """Cổng model bận quá `timeout_s` (HTTP 503 busy); phần nới đã lưu, feature tính ở lần sau."""


def normalize_text(text: str) -> str:
    """NFC, bỏ khoảng trắng đầu/cuối, mọi chuỗi khoảng trắng liên tiếp thành một dấu cách."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def apply_text_edit(segment: Segment, text: str) -> Segment:
    """Câu mới với `text` đã sửa và không còn `translation` (D-16).

    `words` mô tả audio gốc nên chỉ đổi chữ khi số token khớp từng từ (mốc thời gian, asrProb, ipa,
    refConfidence, prominence giữ nguyên); khác số token thì `words` giữ nguyên (Pitfall 9). Dựng
    lại từ dict đã dump để field tuỳ chọn vắng thì vắng hẳn, không bao giờ ghi None.
    """
    raw = segment.model_dump(by_alias=True, exclude_unset=True)
    raw["text"] = text
    raw.pop("translation", None)
    tokens = text.split(" ")
    if len(tokens) == len(segment.words):
        raw["words"] = [
            {**word, "text": token} for word, token in zip(raw["words"], tokens, strict=True)
        ]
    return Segment.model_validate(raw)


def edit_segment_text(lesson_id: str, index: int, text: str) -> Segment:
    """Lưu `text` (đã `normalize_text`) cho câu `index` của bài sẵn sàng; trả Segment mới.

    Raise InvalidIdError / FileNotFoundError (bài không có), InvalidState (bài chưa `ready`),
    IndexError (không có câu này).
    """
    edited: list[Segment] = []

    def mutate(lesson: Lesson) -> Lesson:
        if lesson.status != "ready":
            raise InvalidState("bài chưa sẵn sàng")
        if not 0 <= index < len(lesson.segments):
            raise IndexError(index)
        segments = list(lesson.segments)
        segments[index] = apply_text_edit(segments[index], text)
        edited.append(segments[index])
        return lesson.model_copy(update={"segments": segments})

    store.update_lesson(lesson_id, mutate)
    return edited[0]


def bump_end_extra(lesson_id: str, index: int) -> Segment:
    """`endExtraMs += 300` (kẹp ở trần) và lưu NGAY, trước khi tính lại feature (02-01 mục E).

    Raise ExtendLimit khi đã ở trần; cùng các lỗi như `edit_segment_text`.
    """
    bumped: list[Segment] = []

    def mutate(lesson: Lesson) -> Lesson:
        if lesson.status != "ready":
            raise InvalidState("bài chưa sẵn sàng")
        if not 0 <= index < len(lesson.segments):
            raise IndexError(index)
        current = lesson.segments[index]
        if current.end_extra_ms >= EXTEND_MAX_MS:
            raise ExtendLimit("đã nới tối đa")
        raw = current.model_dump(by_alias=True, exclude_unset=True)
        raw["endExtraMs"] = min(current.end_extra_ms + EXTEND_STEP_MS, EXTEND_MAX_MS)
        segments = list(lesson.segments)
        segments[index] = Segment.model_validate(raw)
        bumped.append(segments[index])
        return lesson.model_copy(update={"segments": segments})

    store.update_lesson(lesson_id, mutate)
    return bumped[0]


def merge_ipa(current: Segment, analyzed: Segment) -> Segment:
    """`current` với `ipa` của từng từ lấy từ `analyzed` (từ không chắc thì không có `ipa`).

    Phân tích chạy lâu và không giữ khoá bài, nên trong lúc đó người dùng có thể đã sửa text hay
    nới tiếp. Chỉ `ipa` là kết quả của lần phân tích; text, translation, endExtraMs mới nhất giữ
    nguyên. `words` không bao giờ đổi số lượng sau khi tạo bài nên ghép theo vị trí là an toàn.
    """
    raw = current.model_dump(by_alias=True, exclude_unset=True)
    if len(current.words) != len(analyzed.words):
        return current
    for word, fresh in zip(raw["words"], analyzed.words, strict=True):
        word.pop("ipa", None)
        if fresh.ipa is not None:
            word["ipa"] = fresh.ipa
    return Segment.model_validate(raw)


def recompute_segment(
    lesson_id: str,
    index: int,
    deps: pipeline.PipelineDeps,
    gate: _Gate,
    timeout_s: float = RECOMPUTE_TIMEOUT_S,
) -> Segment:
    """Tính lại F0/energy/PPG (.npz) và IPA của một câu dưới cổng model; lưu và trả câu mới.

    Chờ cổng tối đa `timeout_s` rồi raise Busy. Model PPG được nạp đúng một lần, luôn được giải
    phóng (`finally`) và cổng luôn được nhả. Raise `pipeline.StepError` nếu thiếu stem của khoảng.
    """
    if not gate.acquire(timeout=timeout_s):
        raise Busy
    try:
        lesson = store.load_lesson(lesson_id)
        if not 0 <= index < len(lesson.segments):
            raise IndexError(index)
        segment = lesson.segments[index]
        vocals16, base_offset = pipeline.load_range_vocals16(lesson)
        ppg_model = deps.load_ppg()
        try:
            vocab = _load_vocab(deps)
            analyzed = pipeline.analyze_segment(
                lesson_id,
                segment,
                vocals16,
                base_offset,
                lesson.duration_sec,
                lesson.pad_ms,
                ppg_model,
                vocab,
                deps,
                StepTimer(),
            )
        finally:
            del ppg_model
            deps.free_memory()
        return _save_analyzed(lesson_id, index, analyzed)
    finally:
        gate.release()


def _load_vocab(deps: pipeline.PipelineDeps) -> Mapping[int, str]:
    """Vocab IPA; thiếu cache thì không có IPA (không chặn thao tác, precision trước recall)."""
    try:
        return deps.load_vocab()
    except Exception:
        logger.warning("không nạp được vocab IPA; câu này không có IPA", exc_info=True)
        return {}


def _save_analyzed(lesson_id: str, index: int, analyzed: Segment) -> Segment:
    merged: list[Segment] = []

    def mutate(lesson: Lesson) -> Lesson:
        segments = list(lesson.segments)
        segments[index] = merge_ipa(segments[index], analyzed)
        merged.append(segments[index])
        return lesson.model_copy(update={"segments": segments})

    store.update_lesson(lesson_id, mutate)
    return merged[0]

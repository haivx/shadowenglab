"""Sửa câu (PLY-04, D-16) trên `lesson.json`: chuẩn hoá text, giữ căn chỉnh từ-âm thanh.

Phần thuần (`normalize_text`, `apply_text_edit`) không đụng đĩa; `edit_segment_text` là chỗ duy nhất
ghi, luôn qua `store.update_lesson` (khoá riêng của bài) để PATCH / extend-end / translate cùng lúc
không làm mất ghi của nhau.
"""

from __future__ import annotations

import unicodedata

from audio_service.contracts_gen import Lesson, Segment
from audio_service.lesson import store
from audio_service.lesson.jobs import InvalidState

TEXT_MAX_CHARS = 500  # 02-01 mục A9: 1-500 ký tự sau khi trim, đếm theo code point NFC


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

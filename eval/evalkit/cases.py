"""Nạp `eval/cases.jsonl`, kiểm bất biến của `EvalCase` và dấu nhận diện câu (04-02, D-05, D-12).

`EvalCase` là contract (Zod -> pydantic) nên shape do `packages/contracts` giữ; các bất biến không
biểu diễn được trong Zod (04-01 mục A5) được kiểm ở đây. Mọi lỗi dữ liệu là `CaseError`, nêu caseId
hoặc số dòng để Liam sửa; script gọi sẽ thoát 2 (không bỏ qua im lặng).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from audio_service.config import REPO_ROOT
from audio_service.contracts_gen import EvalCase, Segment

CASES_PATH = REPO_ROOT / "eval" / "cases.jsonl"

# 04-01 mục A5: errorType theo từ bắt buộc có wordIndex, mức câu không được có.
WORD_LEVEL_TYPES = frozenset(
    {"wrong_stress", "extra_pause", "pitch_off", "weak_form", "final_drop"}
)
SENTENCE_LEVEL_TYPES = frozenset({"flat", "final_rise"})
TEXT_HASH_LEN = 16


class CaseError(ValueError):
    """Dữ liệu case sai (thiếu file, dòng hỏng, vi phạm bất biến, thiếu split)."""


def text_hash(text: str) -> str:
    """16 ký tự hex đầu của sha256(text UTF-8): dấu nhận diện nội dung câu (04-01 mục A3)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:TEXT_HASH_LEN]


def error_type_of(case: EvalCase) -> str | None:
    """Giá trị chuỗi của errorType (pydantic sinh `ErrorType` là RootModel nên đọc bằng `.root`)."""
    return case.error_type.root if case.error_type is not None else None


def load_cases(path: Path) -> list[EvalCase]:
    """Đọc từng dòng `path` thành `EvalCase`, bỏ dòng trống. Thiếu file/dòng hỏng -> CaseError."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise CaseError(
            f"không có {path.name}: chưa có case nào. Viết case bằng tag_clips.py add rồi chạy lại"
        ) from None
    except (OSError, UnicodeDecodeError) as exc:
        raise CaseError(f"không đọc được {path.name} ({type(exc).__name__})") from None
    cases: list[EvalCase] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvalCase.model_validate_json(line))
        except ValidationError:
            raise CaseError(f"{path.name} dòng {number}: không phải một EvalCase hợp lệ") from None
    return cases


def validate_cases(cases: Sequence[EvalCase]) -> None:
    """Kiểm bất biến A5 không cần bài: kind/errorType/wordIndex, caseId và clip duy nhất."""
    seen_ids: set[str] = set()
    seen_clips: dict[str, str] = {}
    for case in cases:
        label = case.case_id
        if label in seen_ids:
            raise CaseError(f"caseId {label} bị trùng")
        seen_ids.add(label)
        error_type = error_type_of(case)
        if case.kind == "error":
            if error_type is None:
                raise CaseError(f"{label}: case lỗi (kind error) phải có errorType")
            if error_type in WORD_LEVEL_TYPES and case.word_index is None:
                raise CaseError(f"{label}: errorType {error_type} bắt buộc có wordIndex")
            if error_type in SENTENCE_LEVEL_TYPES and case.word_index is not None:
                raise CaseError(f"{label}: errorType {error_type} ở mức câu, không có wordIndex")
        else:
            if error_type is not None or case.word_index is not None:
                raise CaseError(f"{label}: case đúng (kind correct) không có errorType/wordIndex")
        if case.clip is not None:
            if case.clip in seen_clips:
                raise CaseError(f"{label}: clip {case.clip} đã gắn cho {seen_clips[case.clip]}")
            seen_clips[case.clip] = label


def stamp_mismatch(case: EvalCase, segment: Segment) -> str | None:
    """So 4 trường dấu nhận diện câu của case với câu hiện tại; None nếu khớp (D-05)."""
    current = {
        "segStartMs": (case.seg_start_ms, round(segment.start * 1000)),
        "segEndMs": (case.seg_end_ms, round(segment.end * 1000)),
        "segEndExtraMs": (case.seg_end_extra_ms, segment.end_extra_ms),
        "segTextHash": (case.seg_text_hash, text_hash(segment.text)),
    }
    diffs = [f"{name} {saved} != {now}" for name, (saved, now) in current.items() if saved != now]
    return "; ".join(diffs) if diffs else None


def select_split(cases: Sequence[EvalCase], *, include_heldout: bool = False) -> list[EvalCase]:
    """Case tuning (và held-out khi `include_heldout`, chưa dùng ở 04-02). Thiếu split -> CaseError.

    A4 / D-12: split chỉ tính được khi đã viết đủ kịch bản, nên còn case chưa chốt thì dừng thay vì
    đoán. Thứ tự trong file được giữ.
    """
    missing = [case.case_id for case in cases if case.split is None]
    if missing:
        listed = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
        raise CaseError(
            f"{len(missing)} case chưa có split ({listed}): chạy tag_clips.py split trước (D-12)"
        )
    wanted = {"tuning", "heldout"} if include_heldout else {"tuning"}
    return [case for case in cases if case.split in wanted]

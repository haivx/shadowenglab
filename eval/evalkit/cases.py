"""Nạp `eval/cases.jsonl`, kiểm bất biến của `EvalCase` và dấu nhận diện câu (04-02, D-05, D-12).

`EvalCase` là contract (Zod -> pydantic) nên shape do `packages/contracts` giữ; các bất biến không
biểu diễn được trong Zod (04-01 mục A5) được kiểm ở đây. Mọi lỗi dữ liệu là `CaseError`, nêu caseId
hoặc số dòng để Liam sửa; script gọi sẽ thoát 2 (không bỏ qua im lặng).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
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
# D-12 / 04-01 mục D1: phần case held-out mong muốn của mỗi tầng (và ngưỡng split câu mới, D2).
HELDOUT_SHARE = 0.30
SPLITS = ("tuning", "heldout")


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


# --- ghi case và chốt split (04-04, D-02, D-12) ------------------------------------------------


def dump_case(case: EvalCase) -> str:
    """Một dòng JSONL của case: camelCase, optional là vắng mặt (không bao giờ null), thứ tự trường
    theo model."""
    payload = case.model_dump(mode="json", by_alias=True, exclude_none=True)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def write_cases(path: Path, cases: Sequence[EvalCase]) -> None:
    """Ghi `path` atomic: validate trước, ghi `<tên>.part` rồi `os.replace` (T-04-10)."""
    validate_cases(cases)
    part = path.with_suffix(path.suffix + ".part")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        part.write_text("".join(dump_case(case) + "\n" for case in cases), encoding="utf-8")
        os.replace(part, path)
    finally:
        part.unlink(missing_ok=True)


def next_case_id(cases: Sequence[EvalCase]) -> str:
    """`c` + 4 chữ số, lớn nhất đang có + 1 (`c0001` khi chưa có case; 04-01 mục A3)."""
    numbers = [
        int(case.case_id[1:])
        for case in cases
        if case.case_id.startswith("c") and case.case_id[1:].isdigit()
    ]
    return f"c{(max(numbers) if numbers else 0) + 1:04d}"


def stamp_for(segment: Segment) -> dict[str, int | str]:
    """4 trường dấu nhận diện câu của `segment` (camelCase như trong file, 04-01 mục A3, D-05)."""
    return {
        "segStartMs": round(segment.start * 1000),
        "segEndMs": round(segment.end * 1000),
        "segEndExtraMs": segment.end_extra_ms,
        "segTextHash": text_hash(segment.text),
    }


def split_fraction(lesson_id: str, index: int) -> float:
    """Vị trí của câu trong [0, 1): 16 hex đầu của sha256 `"{lessonId}:{segmentIndex}"` / 16**16."""
    digest = hashlib.sha256(f"{lesson_id}:{index}".encode()).hexdigest()[:16]
    return int(digest, 16) / 16**16


def stratum(case: EvalCase) -> str:
    """Tầng của case khi chia split: errorType, hoặc `correct` (D-12)."""
    return error_type_of(case) or "correct"


Sentence = tuple[str, int]


def assign_splits(cases: Sequence[EvalCase]) -> dict[Sentence, str]:
    """Split cho mọi câu còn case chưa có split, theo 04-01 mục D1 (D-12). Hàm thuần.

    Câu đã có split ở ít nhất một case thì mọi case của câu nhận split đó. Các câu còn lại duyệt
    theo `split_fraction` tăng dần (hoà thì theo bài, số câu); câu vào held-out nếu với MỌI tầng
    của nó, số case held-out của tầng sau khi thêm không vượt `ceil(0.30 * tổng case của tầng)`.
    Kết quả không phụ thuộc thứ tự `cases`. Trả về các câu CẦN GÁN; câu đã có split ở mọi case
    không nằm trong kết quả, và split đã ghi không bao giờ bị đổi.
    """
    fixed: dict[Sentence, str] = {}
    members: dict[Sentence, list[EvalCase]] = {}
    for case in cases:
        key = (case.lesson_id, case.segment_index)
        members.setdefault(key, []).append(case)
        if case.split is not None:
            side = str(case.split)
            if fixed.setdefault(key, side) != side:
                raise CaseError(f"câu {key[0]}#{key[1]} có case thuộc hai split khác nhau")

    totals: dict[str, int] = {}
    held: dict[str, int] = {}
    for case in cases:
        totals[stratum(case)] = totals.get(stratum(case), 0) + 1
    for key, side in fixed.items():
        if side == "heldout":
            for case in members[key]:
                held[stratum(case)] = held.get(stratum(case), 0) + 1

    assigned: dict[Sentence, str] = {}
    pending = [key for key in members if key not in fixed]
    for key in sorted(pending, key=lambda k: (split_fraction(*k), k)):
        need: dict[str, int] = {}
        for case in members[key]:
            need[stratum(case)] = need.get(stratum(case), 0) + 1
        fits = all(
            held.get(name, 0) + count <= math.ceil(HELDOUT_SHARE * totals[name])
            for name, count in need.items()
        )
        assigned[key] = "heldout" if fits else "tuning"
        if fits:
            for name, count in need.items():
                held[name] = held.get(name, 0) + count
    for key, side in fixed.items():
        if any(case.split is None for case in members[key]):
            assigned[key] = side
    return assigned


def split_for_new_case(cases: Sequence[EvalCase], lesson_id: str, index: int) -> str | None:
    """Split cho case mới viết (04-01 mục D2): câu đã có split -> split đó; nếu bộ case đã chốt
    split thì câu mới nhận `heldout` khi `split_fraction < 0.30`, ngược lại `tuning`; chưa chốt gì
    -> None (để trống, chờ `split`)."""
    for case in cases:
        if case.lesson_id == lesson_id and case.segment_index == index and case.split is not None:
            return str(case.split)
    if not any(case.split is not None for case in cases):
        return None
    return "heldout" if split_fraction(lesson_id, index) < HELDOUT_SHARE else "tuning"


def with_splits(cases: Sequence[EvalCase], sides: dict[Sentence, str]) -> list[EvalCase]:
    """Điền split theo `sides` cho case chưa có; case đã có split được giữ nguyên."""
    return [
        case
        if case.split is not None or (case.lesson_id, case.segment_index) not in sides
        else case.model_copy(update={"split": sides[(case.lesson_id, case.segment_index)]})
        for case in cases
    ]

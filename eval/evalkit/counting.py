"""Đếm TP/FP/FN theo bảng mã D-10 đã duyệt ở 04-01 và khoảng tin cậy Wilson (04-02, EVL-02).

Lát tracer: chỉ mã chính của errorType khớp mới là TP, mọi issue còn lại là FP. Task 2 hoàn thiện
vị trí, mã phụ, `alsoPresent` và các nguồn âm tính (D-07, D-08, D-09, D-11b, D-18).

Hàm thuần: Observation vào, kết quả ra; không đọc file.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from audio_service.contracts_gen import EvalCase
    from audio_service.scoring.scorer import ProsodyScore
    from evalkit.rescore import ClipInput

# Thứ tự `run_rules` (nền của issueRef).
LAYER_C_CODES = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
POOLED = "GỘP"

_PRIMARY = {
    "wrong_stress": "STRESS_MISMATCH",
    "flat": "FLAT_PITCH",
    "extra_pause": "EXTRA_PAUSE",
    "final_rise": "FINAL_CONTOUR",
    "pitch_off": "PITCH_DEVIATION",
}

Source = Literal["error", "correct", "self"]
Outcome = Literal["tp", "fp", "secondary", "also"]


@dataclass(frozen=True)
class Observation:
    """Một lần chấm: case khai báo gì, scorer báo gì. `source` quyết định cách đếm (D-18)."""

    source: Source
    split: str | None
    lesson_id: str
    segment_index: int
    case_id: str | None
    clip: str | None
    error_type: str | None
    word_index: int | None
    also_present: tuple[tuple[str, int | None], ...]
    words: tuple[str, ...]
    issues: tuple[dict[str, Any], ...]
    align_ok: bool
    voiced: bool
    overall: float


@dataclass(frozen=True)
class Verdict:
    """Kết luận cho một issue: mã, từ, và `outcome`."""

    code: str
    word_index: int | None
    outcome: Outcome
    issue: dict[str, Any]


@dataclass
class RuleTally:
    """TP/FP của một mã; `expected` = số case có mã chính này, `found` = số case có TP (C4)."""

    tp: int = 0
    fp: int = 0
    expected: int = 0
    found: int = 0


def observation_from(
    case: EvalCase, clip: ClipInput, score: ProsodyScore | None, *, split: str | None = None
) -> Observation:
    """Dựng Observation từ case và kết quả chấm; `score` None = không có tiếng nên không issue."""
    also = tuple((entry.error_type.root, entry.word_index) for entry in (case.also_present or []))
    return Observation(
        source="error" if case.kind == "error" else "correct",
        split=split if split is not None else case.split,
        lesson_id=case.lesson_id,
        segment_index=case.segment_index,
        case_id=case.case_id,
        clip=case.clip,
        error_type=case.error_type.root if case.error_type is not None else None,
        word_index=case.word_index,
        also_present=also,
        words=tuple(clip.words),
        issues=tuple(score.issues) if score is not None else (),
        align_ok=score.alignment.ok if score is not None else False,
        voiced=score is not None,
        overall=score.overall if score is not None else 0.0,
    )


def classify(obs: Observation) -> list[Verdict]:
    """Phân loại từng issue của một Observation (tracer: mã chính khớp -> tp, còn lại -> fp)."""
    primary = _PRIMARY.get(obs.error_type or "") if obs.source == "error" else None
    verdicts: list[Verdict] = []
    taken = False
    for issue in obs.issues:
        code = str(issue["code"])
        word_index = issue.get("wordIndex")
        outcome: Outcome = "fp"
        if code == primary and not taken:
            outcome, taken = "tp", True
        verdicts.append(Verdict(code, word_index, outcome, issue))
    return verdicts


def tally(observations: Sequence[Observation]) -> dict[str, RuleTally]:
    """TP/FP/expected/found theo mã, cộng dòng `POOLED` gộp mọi mã Lớp C."""
    result: dict[str, RuleTally] = defaultdict(RuleTally)
    for code in LAYER_C_CODES:
        result[code] = RuleTally()
    for obs in observations:
        verdicts = classify(obs)
        for verdict in verdicts:
            if verdict.outcome == "tp":
                result[verdict.code].tp += 1
            elif verdict.outcome == "fp":
                result[verdict.code].fp += 1
        primary = _PRIMARY.get(obs.error_type or "") if obs.source == "error" else None
        if primary is not None:
            result[primary].expected += 1
            if any(v.outcome == "tp" and v.code == primary for v in verdicts):
                result[primary].found += 1
    pooled = RuleTally()
    for code in LAYER_C_CODES:
        pooled.tp += result[code].tp
        pooled.fp += result[code].fp
        pooled.expected += result[code].expected
        pooled.found += result[code].found
    result[POOLED] = pooled
    return dict(result)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    """Khoảng tin cậy Wilson cho tỉ lệ k/n (mặc định 95 %); n = 0 -> None."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high

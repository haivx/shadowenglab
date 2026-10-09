"""Rule engine Lớp C: issue ngữ điệu từ feature và căn thời gian (RUL-01, D-02, D-12, D-13).

Hàm thuần: `RuleInput` vào, `RuleIssue` ra, không model, không file. Mọi ngưỡng đọc từ
`audio_service.scoring.thresholds` (một file có version, D-12); file này không có số ngưỡng nào.
Mỗi rule có cổng chắc chắn: không đủ chắc thì không báo (CLAUDE.md, precision trước recall).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_service.scoring.align import Alignment
from audio_service.scoring.features import ProsodyFeatures
from audio_service.scoring.thresholds import (
    FLAT_RATIO,
    FLAT_REF_MIN_STD_ST,
    MIN_COMMON_VOICED_FRAMES,
)


@dataclass(frozen=True)
class RuleIssue:
    """`issue` là dict camelCase của `Issue` (score.ts); `severity` dùng để chọn tip (D-14)."""

    issue: dict[str, Any]
    severity: float


@dataclass(frozen=True)
class RuleInput:
    """Mọi thứ rule cần. Trục "ref" là trục khung của bản gốc đã cắt lặng (xem `features.py`).

    `user_st_on_ref`: contour người học đặt lên trục bản gốc qua path. `*_prominence`: một giá trị
    mỗi từ, NaN = không xếp hạng. `word_issues_allowed` False khi căn kém (D-02).
    """

    ref: ProsodyFeatures
    user: ProsodyFeatures
    alignment: Alignment
    words: list[str]
    ref_word_frames: list[tuple[int, int]]
    user_word_frames: list[tuple[int, int]]
    user_st_on_ref: np.ndarray
    pitch_range: float
    ref_prominence: np.ndarray
    user_prominence: np.ndarray
    word_issues_allowed: bool


def _finite(values: np.ndarray) -> np.ndarray:
    return values[np.isfinite(values)]


def flat_pitch(inp: RuleInput) -> RuleIssue | None:
    """FLAT_PITCH (D-12): pitchRange < FLAT_RATIO, bản gốc không phẳng, người học phẳng hơn.

    Cổng chắc chắn: cả hai bên đủ MIN_COMMON_VOICED_FRAMES khung có cao độ (thiếu thì chỉ là không
    đo được, không phải giọng phẳng); std(bản gốc) >= FLAT_REF_MIN_STD_ST (bản gốc phẳng thì bỏ
    qua); std(người học) < std(bản gốc) (pitchRange thấp vì dao động quá mức không phải phẳng).
    """
    if not inp.pitch_range < FLAT_RATIO:
        return None
    ref_v, user_v = _finite(inp.ref.f0_st), _finite(inp.user.f0_st)
    if ref_v.size < MIN_COMMON_VOICED_FRAMES or user_v.size < MIN_COMMON_VOICED_FRAMES:
        return None
    ref_sd, user_sd = float(ref_v.std()), float(user_v.std())
    if ref_sd < FLAT_REF_MIN_STD_ST or not user_sd < ref_sd:
        return None
    pitch_range = float(inp.pitch_range)
    return RuleIssue(
        issue={"code": "FLAT_PITCH", "data": {"pitchRange": pitch_range}},
        severity=1.0 - pitch_range,
    )


def final_contour(inp: RuleInput) -> RuleIssue | None:
    return None


def pitch_deviation(inp: RuleInput) -> list[RuleIssue]:
    return []


def extra_pause(inp: RuleInput) -> list[RuleIssue]:
    return []


def stress_mismatch(inp: RuleInput) -> RuleIssue | None:
    return None


def run_rules(inp: RuleInput) -> list[RuleIssue]:
    """Chạy các rule theo thứ tự cố định STRESS_MISMATCH, FINAL_CONTOUR, EXTRA_PAUSE,
    PITCH_DEVIATION, FLAT_PITCH; trong một mã theo chỉ số từ. Thứ tự này là thứ tự `issues`
    (và là cơ sở của `issueRef`).
    """
    issues: list[RuleIssue] = []
    flat = flat_pitch(inp)
    if flat is not None:
        issues.append(flat)
    return issues

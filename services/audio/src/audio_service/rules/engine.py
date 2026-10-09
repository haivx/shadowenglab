"""Rule engine Lớp C: issue ngữ điệu từ feature và căn thời gian (RUL-01, D-02, D-12, D-13).

Hàm thuần: `RuleInput` vào, `RuleIssue` ra, không model, không file. Mọi ngưỡng đọc từ
`audio_service.scoring.thresholds` (một file có version, D-12); file này không có số ngưỡng nào.
Mỗi rule có cổng chắc chắn: không đủ chắc thì không báo (CLAUDE.md, precision trước recall).

Khi căn thời gian kém (`word_issues_allowed` False, D-02) chỉ FLAT_PITCH và FINAL_CONTOUR (rule
mức câu) còn chạy; STRESS_MISMATCH, PITCH_DEVIATION, EXTRA_PAUSE trả rỗng.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import theilslopes

from audio_service.scoring.align import Alignment
from audio_service.scoring.features import HOP_S, ProsodyFeatures
from audio_service.scoring.metrics import sentence_offset
from audio_service.scoring.prominence import (
    ms_to_frames,
    ref_row_at_user_frame,
    silent_runs,
)
from audio_service.scoring.thresholds import (
    FINAL_MIN_VOICED_FRAMES,
    FINAL_SLOPE_MAX_ST_S,
    FINAL_SLOPE_MIN_ST_S,
    FINAL_WINDOW_FRAMES,
    FLAT_RATIO,
    FLAT_REF_MIN_STD_ST,
    MIN_COMMON_VOICED_FRAMES,
    PAUSE_REF_MS,
    PAUSE_USER_MS,
    PAUSE_WORD_SNAP_MS,
    PD_MIN_FRAMES,
    PD_SIGN_CONSISTENCY,
    PD_VOICED_RATIO,
    PITCH_DEVIATION_ST,
    STRESS_MARGIN_Z,
    STRESS_MIN_WORDS,
)

# Hình học của EXTRA_PAUSE theo kế hoạch 03-06 (không phải ngưỡng chấm): đoạn lặng phải cách hai
# đầu bản ghi hơn 3 khung, và bản gốc được tìm đoạn lặng trong +-10 khung quanh vị trí ánh xạ.
_PAUSE_EDGE_FRAMES = 3
_PAUSE_REF_WINDOW_FRAMES = 10
_HOP_MS = HOP_S * 1000.0


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


# --- FLAT_PITCH (mức câu) -------------------------------------------------------------------


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


# --- FINAL_CONTOUR (mức câu) ----------------------------------------------------------------


def _final_slope(st: np.ndarray) -> float | None:
    """Độ dốc Theil-Sen (st/s) của FINAL_WINDOW_FRAMES khung cuối; None nếu quá ít khung hữu hạn."""
    tail = st[-FINAL_WINDOW_FRAMES:]
    seconds = np.arange(tail.size, dtype=np.float64) * HOP_S
    finite = np.isfinite(tail)
    if int(finite.sum()) < FINAL_MIN_VOICED_FRAMES:
        return None
    return float(theilslopes(tail[finite], seconds[finite])[0])


def final_contour(inp: RuleInput) -> RuleIssue | None:
    """FINAL_CONTOUR (D-12): độ dốc F0 ở cuối câu ngược dấu nhau và đều nằm trong dải đo được.

    Cổng chắc chắn: mỗi bên đủ FINAL_MIN_VOICED_FRAMES khung hữu thanh trong cửa sổ cuối; cả hai
    |độ dốc| trong [FINAL_SLOPE_MIN_ST_S, FINAL_SLOPE_MAX_ST_S] (dưới là nhiễu, trên là nghi lỗi
    quãng tám). Dùng contour cuối của chính mỗi bên nên vẫn chạy khi căn kém (D-02).
    """
    ref_slope, user_slope = _final_slope(inp.ref.f0_st), _final_slope(inp.user.f0_st)
    if ref_slope is None or user_slope is None:
        return None
    for slope in (ref_slope, user_slope):
        if not FINAL_SLOPE_MIN_ST_S <= abs(slope) <= FINAL_SLOPE_MAX_ST_S:
            return None
    if ref_slope * user_slope >= 0.0:
        return None
    return RuleIssue(
        issue={
            "code": "FINAL_CONTOUR",
            "data": {"refSlope": round(ref_slope, 1), "userSlope": round(user_slope, 1)},
        },
        severity=abs(user_slope - ref_slope),
    )


# --- PITCH_DEVIATION (theo từ) --------------------------------------------------------------


def pitch_deviation(inp: RuleInput) -> list[RuleIssue]:
    """PITCH_DEVIATION (D-12, D-13): người học lệch bản gốc hơn PITCH_DEVIATION_ST trên một từ.

    Lệch = user - ref trên khung hữu hạn cả hai bên, trừ độ lệch của cả câu (median) để giọng
    cao/thấp hơn không bị tính. Cổng chắc chắn: từ có ít nhất PD_MIN_FRAMES khung chung và
    PD_VOICED_RATIO độ dài từ; median lệch của từ vượt ngưỡng; ít nhất PD_SIGN_CONSISTENCY số
    khung cùng dấu với median. Chỉ khi căn đáng tin (D-02).
    """
    if not inp.word_issues_allowed:
        return []
    ref_st, user_st = inp.ref.f0_st, inp.user_st_on_ref
    n = int(min(ref_st.size, user_st.size))
    both = np.isfinite(ref_st[:n]) & np.isfinite(user_st[:n])
    if not both.any():
        return []
    diff = np.where(both, user_st[:n] - ref_st[:n], np.nan)
    offset = sentence_offset(ref_st[:n], user_st[:n])
    found: list[RuleIssue] = []
    for index, (start, end) in enumerate(inp.ref_word_frames[: len(inp.words)]):
        start, end = max(start, 0), min(end, n)
        length = end - start
        if length <= 0:
            continue
        common = _finite(diff[start:end]) - offset
        if common.size < PD_MIN_FRAMES or common.size < PD_VOICED_RATIO * length:
            continue
        median = float(np.median(common))
        if abs(median) <= PITCH_DEVIATION_ST:
            continue
        if float(np.mean(common * median > 0.0)) < PD_SIGN_CONSISTENCY:
            continue
        found.append(
            RuleIssue(
                issue={
                    "code": "PITCH_DEVIATION",
                    "wordIndex": index,
                    "data": {"meanDiffSt": round(median, 1)},
                },
                severity=abs(median),
            )
        )
    return found


# --- EXTRA_PAUSE (theo từ) ------------------------------------------------------------------


def extra_pause(inp: RuleInput) -> list[RuleIssue]:
    """EXTRA_PAUSE (D-12): người học ngắt >= PAUSE_USER_MS ở chỗ bản gốc không ngắt.

    Mỗi đoạn lặng của người học (mặt nạ tương đối) nằm giữa bản ghi được ánh xạ sang trục bản gốc
    bằng path. Cổng chắc chắn: bản gốc không có đoạn lặng >= PAUSE_REF_MS quanh vị trí đó; tâm đoạn
    cách đuôi một từ không quá PAUSE_WORD_SNAP_MS và chỉ đúng một đuôi từ gần như vậy (tip nói sai
    từ còn tệ hơn bỏ sót); từ đó không phải từ cuối. Chỉ khi căn đáng tin (D-02).
    """
    frames = inp.ref_word_frames[: len(inp.words)]
    path = inp.alignment.path
    if not inp.word_issues_allowed or len(frames) < 2 or path.shape[0] == 0:
        return []
    n_user = int(inp.user.energy_db.size)
    snap = ms_to_frames(PAUSE_WORD_SNAP_MS)
    ref_pauses = silent_runs(inp.ref.energy_db, ms_to_frames(PAUSE_REF_MS))
    ref_silences = silent_runs(inp.ref.energy_db, 1)
    ends = np.array([end for _, end in frames], dtype=np.float64)
    best: dict[int, tuple[float, float]] = {}  # afterWord -> (userMs, refMs)
    for lo, hi in silent_runs(inp.user.energy_db, ms_to_frames(PAUSE_USER_MS)):
        if lo <= _PAUSE_EDGE_FRAMES or n_user - hi <= _PAUSE_EDGE_FRAMES:
            continue
        rows = [ref_row_at_user_frame(path, col) for col in (lo, (lo + hi) // 2, hi - 1)]
        if not all(np.isfinite(rows)):
            continue
        first, centre, last = rows
        window = (
            min(first, last) - _PAUSE_REF_WINDOW_FRAMES,
            max(first, last) + _PAUSE_REF_WINDOW_FRAMES,
        )
        if any(a < window[1] and b > window[0] for a, b in ref_pauses):
            continue
        dists = np.abs(ends - centre)
        after = int(np.argmin(dists))
        if dists[after] > snap or int(np.sum(dists <= snap)) != 1 or after >= len(frames) - 1:
            continue
        ref_ms = (
            max((b - a for a, b in ref_silences if a < window[1] and b > window[0]), default=0)
            * _HOP_MS
        )
        user_ms = (hi - lo) * _HOP_MS
        if after not in best or user_ms > best[after][0]:
            best[after] = (user_ms, ref_ms)
    return [
        RuleIssue(
            issue={
                "code": "EXTRA_PAUSE",
                "wordIndex": after,
                "data": {"refMs": best[after][1], "userMs": best[after][0]},
            },
            severity=best[after][0],
        )
        for after in sorted(best)
    ]


# --- STRESS_MISMATCH (mức câu, gắn với một từ) -----------------------------------------------


def _top_two(prominence: np.ndarray, ranked: np.ndarray) -> tuple[int, float]:
    """(chỉ số từ nổi nhất, biên so với từ thứ hai) trong các từ `ranked`."""
    order = ranked[np.argsort(-prominence[ranked], kind="stable")]
    return int(order[0]), float(prominence[order[0]] - prominence[order[1]])


def stress_mismatch(inp: RuleInput) -> RuleIssue | None:
    """STRESS_MISMATCH (D-12): từ nổi nhất khác nhau, mỗi bên vượt từ thứ hai >= STRESS_MARGIN_Z.

    Cổng chắc chắn: ít nhất STRESS_MIN_WORDS từ có prominence hữu hạn ở CẢ HAI bên (từ NaN không
    xếp hạng). Không hạ STRESS_MARGIN_Z cho có tip (Phase 4 chỉnh). Chỉ khi căn đáng tin (D-02).
    """
    if not inp.word_issues_allowed:
        return None
    n = min(inp.ref_prominence.size, inp.user_prominence.size, len(inp.words))
    ref_p, user_p = inp.ref_prominence[:n], inp.user_prominence[:n]
    ranked = np.flatnonzero(np.isfinite(ref_p) & np.isfinite(user_p))
    if ranked.size < STRESS_MIN_WORDS:
        return None
    ref_top, ref_margin = _top_two(ref_p, ranked)
    user_top, user_margin = _top_two(user_p, ranked)
    if ref_top == user_top or min(ref_margin, user_margin) < STRESS_MARGIN_Z:
        return None
    return RuleIssue(
        issue={
            "code": "STRESS_MISMATCH",
            "wordIndex": ref_top,
            "data": {"refWord": inp.words[ref_top], "userWord": inp.words[user_top]},
        },
        severity=min(ref_margin, user_margin),
    )


def run_rules(inp: RuleInput) -> list[RuleIssue]:
    """Chạy các rule theo thứ tự cố định STRESS_MISMATCH, FINAL_CONTOUR, EXTRA_PAUSE,
    PITCH_DEVIATION, FLAT_PITCH; trong một mã theo chỉ số từ. Thứ tự này là thứ tự `issues`
    (và là cơ sở của `issueRef`).
    """
    issues: list[RuleIssue] = []
    for single in (stress_mismatch(inp), final_contour(inp)):
        if single is not None:
            issues.append(single)
    issues.extend(extra_pause(inp))
    issues.extend(pitch_deviation(inp))
    flat = flat_pitch(inp)
    if flat is not None:
        issues.append(flat)
    return issues

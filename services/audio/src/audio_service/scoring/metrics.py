"""Ba chỉ số ngữ điệu và các hàm dựng contour/từ (PRO-02, D-04, D-05, D-06).

Hàm thuần trên mảng theo khung 10 ms (xem `features.py`). Giá trị chưa được kẹp về [0, 1] ở đây khi
không cần; `scorer.py` đặt hàng rào hữu hạn cuối cùng.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

import numpy as np

from audio_service.scoring.features import HOP_S
from audio_service.scoring.thresholds import (
    MIN_COMMON_VOICED_FRAMES,
    PAUSE_SILENCE_DB_BELOW_P95,
    PAUSE_USER_MS,
    SIMILARITY_MIN_FRAMES,
    SIMILARITY_RMS_ST,
)

_CONST_STD = 1e-6  # độ lệch chuẩn nhỏ hơn mức này coi là phẳng tuyệt đối
_HOP_MS = HOP_S * 1000.0


class _Timed(Protocol):
    @property
    def start_s(self) -> float: ...

    @property
    def end_s(self) -> float: ...


def _true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Các đoạn True liên tiếp [start, end) của mặt nạ."""
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return list(zip(starts.tolist(), ends.tolist(), strict=True))


def speech_frames(db: np.ndarray) -> int:
    """Số khung "thời gian có tiếng": tổng khung trừ các đoạn lặng >= 250 ms.

    Lặng = dB <= p95 - 35 (mặt nạ tương đối, bất biến theo mức tín hiệu; RESEARCH Pattern 3).
    Khe lặng ngắn hơn 250 ms vẫn tính là thời gian nói.
    """
    if db.size == 0:
        return 0
    silent = db <= float(np.percentile(db, 95)) - PAUSE_SILENCE_DB_BELOW_P95
    min_run = int(round(PAUSE_USER_MS / _HOP_MS))
    removed = sum(hi - lo for lo, hi in _true_runs(silent) if hi - lo >= min_run)
    return int(db.size - removed)


def speed(ref_db: np.ndarray, user_db: np.ndarray) -> float:
    """min(r, 1/r) với r = thời gian có tiếng của người học / của bản gốc; 0 khi một bên bằng 0."""
    ref_n, user_n = speech_frames(ref_db), speech_frames(user_db)
    if ref_n == 0 or user_n == 0:
        return 0.0
    r = user_n / ref_n
    return min(r, 1.0 / r)


def pitch_range(ref_st: np.ndarray, user_st: np.ndarray) -> float:
    """min(r, 1/r) với r = std(semitone người học) / std(semitone bản gốc) trên frame hữu hạn.

    Cả hai phẳng tuyệt đối -> 1.0; đúng một bên phẳng -> 0.0; ít hơn MIN_COMMON_VOICED_FRAMES frame
    hữu hạn ở một bên -> 0.0.
    """
    ref_v, user_v = ref_st[np.isfinite(ref_st)], user_st[np.isfinite(user_st)]
    if ref_v.size < MIN_COMMON_VOICED_FRAMES or user_v.size < MIN_COMMON_VOICED_FRAMES:
        return 0.0
    ref_sd, user_sd = float(ref_v.std()), float(user_v.std())
    ref_flat, user_flat = ref_sd < _CONST_STD, user_sd < _CONST_STD
    if ref_flat and user_flat:
        return 1.0
    if ref_flat or user_flat:
        return 0.0
    r = user_sd / ref_sd
    return min(r, 1.0 / r)


def user_on_ref_axis(user_values: np.ndarray, path: np.ndarray, n_ref: int) -> np.ndarray:
    """Với mỗi khung bản gốc: trung bình giá trị người học mà path ghép vào; NaN nếu không có."""
    out = np.full(n_ref, np.nan, dtype=np.float64)
    if path.shape[0] == 0 or user_values.size == 0 or n_ref == 0:
        return out
    rows, cols = path[:, 0], path[:, 1]
    inside = (rows >= 0) & (rows < n_ref) & (cols >= 0) & (cols < user_values.size)
    vals = user_values[cols[inside]]
    finite = np.isfinite(vals)
    rows = rows[inside][finite]
    sums = np.zeros(n_ref)
    counts = np.zeros(n_ref)
    np.add.at(sums, rows, vals[finite])
    np.add.at(counts, rows, 1.0)
    has = counts > 0
    out[has] = sums[has] / counts[has]
    return out


def melody_match(ref_st: np.ndarray, user_on_ref: np.ndarray) -> float:
    """max(0, Pearson) của hai contour semitone trên frame hữu hạn cả hai bên (D-05).

    Ít hơn MIN_COMMON_VOICED_FRAMES frame chung hoặc một bên không đổi -> 0.0.
    """
    both = np.isfinite(ref_st) & np.isfinite(user_on_ref)
    if int(both.sum()) < MIN_COMMON_VOICED_FRAMES:
        return 0.0
    a, b = ref_st[both], user_on_ref[both]
    if float(a.std()) < _CONST_STD or float(b.std()) < _CONST_STD:
        return 0.0
    return max(0.0, float(np.corrcoef(a, b)[0, 1]))


def _round_points(values: np.ndarray) -> list[float | None]:
    return [round(float(v), 1) if math.isfinite(v) else None for v in values]


def contour_points(
    ref_st: np.ndarray, user_on_ref: np.ndarray, step: int = 2
) -> tuple[list[float | None], list[float | None]]:
    """Hai contour lấy mẫu mỗi `step` khung (20 ms), làm tròn 0.1 st, NaN -> None."""
    return _round_points(ref_st[::step]), _round_points(user_on_ref[::step])


def word_frames(ref_words: Sequence[_Timed], trim_start: int, n_ref: int) -> list[tuple[int, int]]:
    """(start, end) khung của từng từ trên trục bản gốc đã cắt, kẹp trong [0, n_ref]."""
    frames: list[tuple[int, int]] = []
    for word in ref_words:
        start = int(round(word.start_s / HOP_S)) - trim_start
        end = int(round(word.end_s / HOP_S)) - trim_start
        start = min(max(start, 0), n_ref)
        frames.append((start, min(max(end, start), n_ref)))
    return frames


def word_bounds(
    frames: Sequence[tuple[int, int]], step: int = 2, length: int | None = None
) -> list[int]:
    """Điểm contour bắt đầu mỗi từ: start // step, tăng chặt; nếu biết `length` thì < length."""
    bounds: list[int] = []
    for start, _ in frames:
        bound = start // step
        if bounds and bound <= bounds[-1]:
            bound = bounds[-1] + 1
        bounds.append(bound)
    if length is not None and length > 0:
        for i in range(len(bounds) - 1, -1, -1):
            limit = length - 1 - (len(bounds) - 1 - i)
            bounds[i] = max(0, min(bounds[i], limit))
    return bounds


def sentence_offset(ref_st: np.ndarray, user_on_ref: np.ndarray) -> float:
    """Median của (người học - bản gốc) trên frame chung; 0 khi không có frame chung."""
    both = np.isfinite(ref_st) & np.isfinite(user_on_ref)
    if not both.any():
        return 0.0
    return float(np.median(user_on_ref[both] - ref_st[both]))


def word_similarity(
    ref_st: np.ndarray,
    user_on_ref: np.ndarray,
    frames: Sequence[tuple[int, int]],
    offset: float,
    melody: float,
) -> list[float]:
    """Độ giống ngữ điệu từng từ (03-01 mục G): 1 - min(1, RMS(lệch - offset) / 6 st).

    Dưới SIMILARITY_MIN_FRAMES frame chung trong từ thì dùng melodyMatch của câu.
    """
    out: list[float] = []
    for start, end in frames:
        ref_w, user_w = ref_st[start:end], user_on_ref[start:end]
        both = np.isfinite(ref_w) & np.isfinite(user_w)
        if int(both.sum()) < SIMILARITY_MIN_FRAMES:
            out.append(melody)
            continue
        rms = float(np.sqrt(np.mean((user_w[both] - ref_w[both] - offset) ** 2)))
        out.append(1.0 - min(1.0, rms / SIMILARITY_RMS_ST))
    return out


def ref_frame_to_user_seconds(frame: int, path: np.ndarray, user_trim_start: int) -> float:
    """Giây trên bản ghi người học ứng với khung `frame` của bản gốc, qua path (rỗng: 0.0)."""
    if path.shape[0] == 0:
        return 0.0
    idx = int(np.searchsorted(path[:, 0], frame, side="left"))
    idx = min(idx, path.shape[0] - 1)
    return (int(path[idx, 1]) + user_trim_start) * HOP_S

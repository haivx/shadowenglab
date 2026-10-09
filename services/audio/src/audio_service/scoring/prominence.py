"""Prominence từng từ, ghép từ người học qua path và ngắt nghỉ giữa từ (PRO-02, product.md Lớp B).

Hàm thuần trên mảng theo khung 10 ms (xem `features.py`), không model, không file. Công thức
prominence là công thức của product.md; mọi ngưỡng đọc từ `thresholds.py` (D-12).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from audio_service.scoring.features import HOP_S
from audio_service.scoring.metrics import _true_runs
from audio_service.scoring.thresholds import (
    PAUSE_REF_MS,
    PAUSE_SILENCE_DB_BELOW_P95,
    PAUSE_WORD_SNAP_MS,
    PROMINENCE_MIN_VOICED_FRAMES,
)

# Trọng số công thức product.md Lớp B: 0.4·z(F0 max) + 0.4·z(cường độ max) + 0.2·z(độ dài).
_W_F0 = 0.4
_W_ENERGY = 0.4
_W_DURATION = 0.2
_STD_FLOOR = 1e-6  # độ lệch chuẩn nhỏ hơn mức này: z = 0 (các từ giống hệt nhau)
_HOP_MS = HOP_S * 1000.0


def ms_to_frames(ms: float) -> int:
    """Số khung 10 ms gần nhất với `ms` mili giây."""
    return int(round(ms / _HOP_MS))


def _z(values: np.ndarray) -> np.ndarray:
    return (values - values.mean()) / max(float(values.std()), _STD_FLOOR)


def word_prominence(
    st: np.ndarray, energy_db: np.ndarray, frames: Sequence[tuple[int, int]]
) -> np.ndarray:
    """Prominence từng từ: 0.4·z(max st) + 0.4·z(max dB) + 0.2·z(độ dài khung), z trong câu.

    Từ có ít hơn PROMINENCE_MIN_VOICED_FRAMES khung st hữu hạn (hoặc không có khung) -> NaN và
    không tham gia z-score. Trả mảng độ dài `len(frames)`.
    """
    n = len(frames)
    f0_max = np.full(n, np.nan)
    db_max = np.full(n, np.nan)
    length = np.full(n, np.nan)
    for i, (start, end) in enumerate(frames):
        lo, hi = max(start, 0), min(end, int(st.size), int(energy_db.size))
        if hi <= lo:
            continue
        seg = st[lo:hi]
        finite = seg[np.isfinite(seg)]
        if finite.size < PROMINENCE_MIN_VOICED_FRAMES:
            continue
        f0_max[i] = float(finite.max())
        db_max[i] = float(energy_db[lo:hi].max())
        length[i] = float(hi - lo)
    out = np.full(n, np.nan)
    valid = np.isfinite(f0_max) & np.isfinite(db_max)
    if valid.any():
        out[valid] = (
            _W_F0 * _z(f0_max[valid])
            + _W_ENERGY * _z(db_max[valid])
            + _W_DURATION * _z(length[valid])
        )
    return out


def user_word_frames(
    ref_frames: Sequence[tuple[int, int]], path: np.ndarray, n_user: int
) -> list[tuple[int, int]]:
    """Khoảng khung người học mà path ghép vào từng từ của bản gốc; (0, 0) nếu không có."""
    out: list[tuple[int, int]] = []
    if path.shape[0] == 0 or n_user <= 0:
        return [(0, 0) for _ in ref_frames]
    rows, cols = path[:, 0], path[:, 1]
    for start, end in ref_frames:
        lo = int(np.searchsorted(rows, start, side="left"))
        hi = int(np.searchsorted(rows, end, side="left"))
        if end <= start or hi <= lo:
            out.append((0, 0))
            continue
        first = int(cols[lo:hi].min())
        last = int(cols[lo:hi].max()) + 1
        out.append((min(max(first, 0), n_user), min(max(last, 0), n_user)))
    return out


def stress_entries(
    words: Sequence[str], ref_prom: np.ndarray, user_prom: np.ndarray
) -> list[dict[str, Any]]:
    """`{word, ref, user}` mỗi từ; NaN ghi 0.0 (contract cần số, rule loại NaN khỏi xếp hạng)."""
    return [
        {
            "word": word,
            "ref": float(r) if np.isfinite(r) else 0.0,
            "user": float(u) if np.isfinite(u) else 0.0,
        }
        for word, r, u in zip(words, ref_prom, user_prom, strict=True)
    ]


def silent_mask(energy_db: np.ndarray) -> np.ndarray:
    """Khung lặng: dB <= p95 - PAUSE_SILENCE_DB_BELOW_P95 (mặt nạ tương đối, bất biến mức)."""
    if energy_db.size == 0:
        return np.zeros(0, dtype=bool)
    return energy_db <= float(np.percentile(energy_db, 95)) - PAUSE_SILENCE_DB_BELOW_P95


def silent_runs(energy_db: np.ndarray, min_frames: int) -> list[tuple[int, int]]:
    """Các đoạn lặng liên tiếp [start, end) dài ít nhất `min_frames` khung (tối thiểu 1)."""
    floor = max(min_frames, 1)
    return [(lo, hi) for lo, hi in _true_runs(silent_mask(energy_db)) if hi - lo >= floor]


def ref_row_at_user_frame(path: np.ndarray, col: int) -> float:
    """Khung bản gốc mà path ghép với khung người học `col` (median nếu nhiều); NaN nếu path rỗng.

    `col` bị bước (1, 2) bỏ qua thì lấy cột gần nhất có trong path.
    """
    if path.shape[0] == 0:
        return float("nan")
    cols = path[:, 1]
    lo = int(np.searchsorted(cols, col, side="left"))
    hi = int(np.searchsorted(cols, col, side="right"))
    if hi > lo:
        return float(np.median(path[lo:hi, 0]))
    after = min(lo, path.shape[0] - 1)
    before = max(lo - 1, 0)
    pick = after if abs(int(cols[after]) - col) <= abs(int(cols[before]) - col) else before
    return float(path[pick, 0])


def pause_entries(
    ref_db: np.ndarray,
    user_db: np.ndarray,
    ref_frames: Sequence[tuple[int, int]],
    path: np.ndarray,
) -> list[dict[str, Any]]:
    """Ngắt giữa các từ liên tiếp: `{afterWord, refMs, userMs}` khi max(refMs, userMs) >= 100.

    refMs = số khung lặng của bản gốc trong khe giữa hai từ. userMs = tổng các đoạn lặng của người
    học mà path ghép (qua tâm đoạn) vào khe đó, cách khe tối đa PAUSE_WORD_SNAP_MS.
    """
    gaps = [(ref_frames[i][1], ref_frames[i + 1][0]) for i in range(len(ref_frames) - 1)]
    if not gaps:
        return []
    snap = ms_to_frames(PAUSE_WORD_SNAP_MS)
    ref_mask = silent_mask(ref_db)
    user_frames = [0] * len(gaps)
    for lo, hi in _true_runs(silent_mask(user_db)):
        centre = ref_row_at_user_frame(path, (lo + hi) // 2)
        if not np.isfinite(centre):
            continue
        dists = [max(min(a, b) - centre, centre - max(a, b), 0.0) for a, b in gaps]
        best = int(np.argmin(dists))
        if dists[best] <= snap:
            user_frames[best] += hi - lo
    entries: list[dict[str, Any]] = []
    for i, (g0, g1) in enumerate(gaps):
        ref_ms = float(ref_mask[max(g0, 0) : max(g1, 0)].sum()) * _HOP_MS
        user_ms = user_frames[i] * _HOP_MS
        if max(ref_ms, user_ms) >= PAUSE_REF_MS:
            entries.append({"afterWord": i, "refMs": ref_ms, "userMs": user_ms})
    return entries

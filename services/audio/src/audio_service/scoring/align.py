"""Căn thời gian người học <-> bản gốc bằng DTW trên MFCC (D-01), sau một giao diện thay được.

Hàm thuần: mảng vào, mảng ra, không model. Phase 5 thay bằng PPG-DTW bằng cách truyền một `Aligner`
khác vào `score_prosody`; rule Lớp C chỉ dùng `Alignment.path` và `Alignment.ok`.

Chống DoS (T-03-05): tỉ lệ độ dài được kiểm TRƯỚC khi dựng ma trận (RESEARCH Pitfall 6), khoảng cách
tính bằng khai triển BLAS, không broadcast 3 chiều.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from audio_service.scoring.thresholds import (
    ALIGN_COST_MAX,
    ALIGN_RATIO_MAX,
    ALIGN_RATIO_MIN,
    ALIGN_SLACK_FRAMES,
)

logger = logging.getLogger(__name__)

_INF = 1e18
_CANCELLATION_TOL = 1e-12  # sai số tương đối của ||a||^2 + ||b||^2 - 2a.b khi a ~ b


@dataclass(frozen=True)
class Alignment:
    """path: (K, 2) int64 (khung bản gốc, khung người học), không giảm theo cả hai cột.

    cost: chi phí DTW chuẩn hoá theo số bước (inf khi không có đường đi). ratio: n_user / n_ref.
    ok: căn đáng tin (D-02). linear: path là đường tỉ lệ thời gian, không phải đường DTW.
    """

    path: np.ndarray
    cost: float
    ratio: float
    ok: bool
    linear: bool


class Aligner(Protocol):
    def __call__(self, ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment: ...


def linear_path(n_ref: int, n_user: int) -> np.ndarray:
    """Mỗi khung bản gốc i ứng với khung người học round(i*(n_user-1)/(n_ref-1)). (K, 2) int64."""
    if n_ref <= 0 or n_user <= 0:
        return np.zeros((0, 2), dtype=np.int64)
    ref = np.arange(n_ref, dtype=np.int64)
    if n_ref == 1:
        return np.stack([ref, np.zeros(1, dtype=np.int64)], axis=1)
    user = np.rint(ref * (n_user - 1) / (n_ref - 1)).astype(np.int64)
    return np.stack([ref, user], axis=1)


def pairwise_dist(ref: np.ndarray, user: np.ndarray) -> np.ndarray:
    """Euclid / sqrt(d) giữa mọi cặp khung, bằng khai triển ||a||^2 + ||b||^2 - 2a.b (BLAS)."""
    a = np.asarray(ref, dtype=np.float64)
    b = np.asarray(user, dtype=np.float64)
    norms = (a * a).sum(axis=1)[:, None] + (b * b).sum(axis=1)[None, :]
    d2 = norms - 2.0 * (a @ b.T)
    # Khai triển triệt tiêu: hai khung giống hệt vẫn ra ~1e-14 thay vì 0. Gọt nhiễu số học đó
    # (ngưỡng tương đối rất nhỏ, thua mọi khoảng cách thật cỡ 0.1 trở lên).
    d2 = np.where(d2 <= _CANCELLATION_TOL * norms, 0.0, d2)
    return np.sqrt(d2) / np.sqrt(a.shape[1])


def dtw_slack(cost_matrix: np.ndarray, slack: int = ALIGN_SLACK_FRAMES) -> tuple[np.ndarray, float]:
    """DTW tập bước {(1,1),(1,2),(2,1)}, vector hoá theo hàng bản gốc.

    Điểm bắt đầu tự do ở cột 0..slack, điểm kết thúc tự do ở `slack` cột cuối (trục người học).
    Trả (path đủ mọi khung bản gốc, chi phí / số bước đã đi) hoặc (rỗng, inf) khi không có đường đi
    (tỉ lệ ngoài [0.5, 2]). Bước (2,1) bỏ qua một hàng; hàng đó được gán cùng khung người học với
    hàng kề để path phủ đủ mọi khung bản gốc.
    """
    n, m = cost_matrix.shape
    acc = np.full((n + 1, m + 1), _INF)
    acc[0, : min(slack + 1, m + 1)] = 0.0
    back = np.zeros((n + 1, m + 1), dtype=np.int8)
    cols = np.arange(m)
    for i in range(1, n + 1):
        c0 = acc[i - 1, 0:m]
        c1 = np.full(m, _INF)
        c1[1:] = acc[i - 1, 0 : m - 1]
        c2 = acc[i - 2, 0:m] if i >= 2 else np.full(m, _INF)
        stack = np.stack([c0, c1, c2])
        k = stack.argmin(axis=0)
        acc[i, 1:] = stack[k, cols] + cost_matrix[i - 1]
        back[i, 1:] = k
    lo = max(1, m - slack)
    j = lo + int(np.argmin(acc[n, lo : m + 1]))
    total = float(acc[n, j])
    if total >= _INF / 2:
        return np.zeros((0, 2), dtype=np.int64), float("inf")
    path: list[tuple[int, int]] = []
    steps = 0
    i = n
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        steps += 1
        step = back[i, j]
        if step == 0:
            i, j = i - 1, j - 1
        elif step == 1:
            i, j = i - 1, j - 2
        else:
            path.append((i - 2, j - 1))
            i, j = i - 2, j - 1
    path.reverse()
    return np.asarray(path, dtype=np.int64), total / max(steps, 1)


def align(ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment:
    """Căn MFCC hai phía (D-01). Căn kém -> đường tỉ lệ thời gian, ok=False (D-02)."""
    n_ref, n_user = int(len(ref_mfcc)), int(len(user_mfcc))
    ratio = n_user / n_ref if n_ref else 0.0
    if n_ref < 2 or n_user < 2 or not (ALIGN_RATIO_MIN <= ratio <= ALIGN_RATIO_MAX):
        result = Alignment(linear_path(n_ref, n_user), float("inf"), ratio, False, True)
    else:
        path, cost = dtw_slack(pairwise_dist(ref_mfcc, user_mfcc), ALIGN_SLACK_FRAMES)
        if path.shape[0] > 0 and cost <= ALIGN_COST_MAX:
            result = Alignment(path, cost, ratio, True, False)
        else:
            result = Alignment(linear_path(n_ref, n_user), cost, ratio, False, True)
    logger.info("align cost=%.3f ratio=%.2f ok=%s", result.cost, result.ratio, result.ok)
    return result

"""Nhãn chất lượng audio từ hai stem của Demucs (D-09, D-23). Hàm thuần: mảng vào, giá trị ra."""

from __future__ import annotations

from typing import Literal

import numpy as np

# Ngưỡng tạm thời (01-01 mục 7), chính thức ở P1/P5 - D-09.
MUSIC_THRESHOLD_DB: float = -15.0

_EPS = 1e-9


def non_vocal_ratio(vocals: np.ndarray, no_vocals: np.ndarray) -> float:
    """Tỉ lệ công suất trung bình no_vocals / vocals (tích luỹ bằng float64)."""
    v = np.asarray(vocals, dtype=np.float64)
    nv = np.asarray(no_vocals, dtype=np.float64)
    if v.size == 0 or nv.size == 0:
        raise ValueError("vocals và no_vocals không được rỗng")
    if v.shape != nv.shape:
        raise ValueError(f"vocals {v.shape} và no_vocals {nv.shape} phải cùng shape")
    return float(np.mean(nv**2) / (np.mean(v**2) + _EPS))


def audio_quality_label(
    ratio: float, threshold_db: float = MUSIC_THRESHOLD_DB
) -> Literal["clean", "music"]:
    """'music' chỉ khi ratio lớn hơn hẳn ngưỡng; so ở miền tỉ lệ để biên chính xác."""
    return "music" if ratio > 10 ** (threshold_db / 10) else "clean"

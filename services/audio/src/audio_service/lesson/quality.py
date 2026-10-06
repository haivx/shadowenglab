"""Nhãn chất lượng audio (RED stub: chưa hiện thực)."""

from __future__ import annotations

from typing import Literal

import numpy as np

MUSIC_THRESHOLD_DB: float = -15.0


def non_vocal_ratio(vocals: np.ndarray, no_vocals: np.ndarray) -> float:
    return 0.0


def audio_quality_label(
    ratio: float, threshold_db: float = MUSIC_THRESHOLD_DB
) -> Literal["clean", "music"]:
    return "clean"

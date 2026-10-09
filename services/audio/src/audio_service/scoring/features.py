"""Feature ngữ điệu (khung RED của 03-03: giao diện có mặt, chưa có hành vi)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FEAT_VERSION = "pf-1"
HOP_S = 0.01


@dataclass(frozen=True)
class ProsodyFeatures:
    f0_st: np.ndarray
    voiced: np.ndarray
    energy_db: np.ndarray
    mfcc: np.ndarray
    trim_start: int
    trim_end: int


def prepare_features(audio16k: np.ndarray) -> ProsodyFeatures:
    return ProsodyFeatures(
        f0_st=np.zeros(0),
        voiced=np.zeros(0, dtype=bool),
        energy_db=np.zeros(0),
        mfcc=np.zeros((0, 12)),
        trim_start=0,
        trim_end=0,
    )

"""Căn thời gian MFCC (khung RED của 03-03: giao diện có mặt, chưa có hành vi)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Alignment:
    path: np.ndarray
    cost: float
    ratio: float
    ok: bool
    linear: bool


class Aligner(Protocol):
    def __call__(self, ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment: ...


def align(ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment:
    return Alignment(
        path=np.zeros((0, 2), dtype=np.int64), cost=float("inf"), ratio=0.0, ok=False, linear=True
    )

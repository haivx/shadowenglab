"""Prominence từng từ và ngắt nghỉ giữa từ (khung RED của 03-06: chưa tính gì)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


def word_prominence(
    st: np.ndarray, energy_db: np.ndarray, frames: Sequence[tuple[int, int]]
) -> np.ndarray:
    return np.zeros(len(frames))


def stress_entries(
    words: Sequence[str], ref_prom: np.ndarray, user_prom: np.ndarray
) -> list[dict[str, Any]]:
    return []


def silent_runs(energy_db: np.ndarray, min_frames: int) -> list[tuple[int, int]]:
    return []


def pause_entries(
    ref_db: np.ndarray,
    user_db: np.ndarray,
    ref_frames: Sequence[tuple[int, int]],
    path: np.ndarray,
) -> list[dict[str, Any]]:
    return []

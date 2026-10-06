"""Tách giọng bằng Demucs htdemucs chạy trong tiến trình, MPS khi có (D-23).

Model id lấy từ `audio_service.models` (không đổi/thay model, D-22/D-23/D-24). `hf://` buộc
trọng số đi qua HF hub (không rơi về repo AWS cũ), khớp `setup_models.ensure_demucs`.
Chỉ các knob không phải model: shifts=0, overlap=0.25, split=True, thiết bị (D-26, item 8).
"""

from __future__ import annotations

import gc
import logging
from typing import TYPE_CHECKING

import numpy as np
import torch

from audio_service.models import DEMUCS_MODEL

if TYPE_CHECKING:
    from demucs.api import Separator

logger = logging.getLogger(__name__)


def pick_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def load_separator(device: str) -> Separator:
    from demucs.api import Separator

    return Separator(
        model=f"hf://{DEMUCS_MODEL}",
        device=device,
        shifts=0,
        overlap=0.25,
        split=True,
    )


def separate_vocals(
    stereo: np.ndarray, sr: int, separator: Separator
) -> tuple[np.ndarray, np.ndarray]:
    """(2, n) float32 -> (vocals, no_vocals), mỗi cái (2, n) float32.

    `no_vocals` là tổng mọi stem không phải vocals (item 8).
    """
    _, stems = separator.separate_tensor(torch.from_numpy(np.ascontiguousarray(stereo)), sr)
    vocals = stems["vocals"].detach().cpu().numpy().astype(np.float32)
    rest = [t.detach().cpu().numpy() for name, t in stems.items() if name != "vocals"]
    no_vocals = np.sum(rest, axis=0).astype(np.float32)
    return vocals, no_vocals


def free_accelerator_memory() -> None:
    """Giải phóng bộ nhớ giữa các stage (máy 8 GB, Pitfall 10, T-01-17)."""
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

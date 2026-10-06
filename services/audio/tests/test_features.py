"""Test feature bản gốc (D-24, D-05): F0, năng lượng, cửa sổ segment, PPG với fallback MPS -> CPU.

Không nạp model thật: PPG dùng model/extractor giả có cùng giao diện.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from audio_service.lesson.features import (
    PpgModel,
    compute_ppg,
    extract_f0,
    frame_energy,
    segment_window,
)

SR = 16000


def _sine(freq: float, seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(SR * seconds)) / SR
    return (amp * np.sin(2 * math.pi * freq * t)).astype(np.float32)


# --- F0 / năng lượng -------------------------------------------------------------------------


def test_f0_of_200_hz_sine_is_about_100_frames_at_200_hz() -> None:
    f0 = extract_f0(_sine(200.0, 1.0))

    assert f0.dtype == np.float32
    assert 95 <= len(f0) <= 101  # bước 10 ms
    voiced = f0[f0 > 0]
    assert len(voiced) > 80
    assert 195.0 <= float(np.median(voiced)) <= 205.0


def test_f0_of_silence_is_all_unvoiced() -> None:
    f0 = extract_f0(np.zeros(SR, dtype=np.float32))

    assert float(f0.max()) == 0.0


@pytest.mark.parametrize("n", [0, 1, 159, 160, 161, 16000, 16001, 23456])
def test_energy_has_one_frame_per_10ms_hop(n: int) -> None:
    energy = frame_energy(np.ones(n, dtype=np.float32))

    assert energy.dtype == np.float32
    assert len(energy) == -(-n // 160)


def test_energy_of_sine_is_its_rms_away_from_the_edges() -> None:
    energy = frame_energy(_sine(200.0, 1.0, amp=0.5))

    assert float(np.median(energy)) == pytest.approx(0.5 / math.sqrt(2), rel=0.05)


def test_energy_is_zero_for_silence() -> None:
    assert float(frame_energy(np.zeros(SR, dtype=np.float32)).max()) == 0.0


# --- cửa sổ segment (D-05) -------------------------------------------------------------------


def test_segment_window_pads_both_sides_and_adds_end_extra() -> None:
    assert segment_window(1.0, 2.0, 150, 300, lo=0.0, hi=10.0) == (0.85, 2.45)


def test_segment_window_clamps_at_lo_and_hi() -> None:
    assert segment_window(0.05, 9.95, 150, 300, lo=0.0, hi=10.0) == (0.0, 10.0)
    assert segment_window(5.0, 6.0, 150, 0, lo=4.9, hi=6.1) == (4.9, 6.1)


def test_segment_window_without_pad_is_the_segment_itself() -> None:
    assert segment_window(1.25, 3.5, 0, 0, lo=0.0, hi=10.0) == (1.25, 3.5)


# --- PPG: fallback MPS -> CPU ----------------------------------------------------------------


class _FakeInput:
    def to(self, device: str) -> _FakeInput:
        return self


class _FakeExtractor:
    def __call__(self, audio: np.ndarray, sampling_rate: int, return_tensors: str) -> object:
        assert sampling_rate == SR
        assert return_tensors == "pt"
        return SimpleNamespace(input_values=_FakeInput())


class _FakeModel:
    """Giống Wav2Vec2ForCTC: `.to(device)` và gọi được; lỗi khi đang ở MPS."""

    def __init__(self, *, fail_on: str | None) -> None:
        self.device = "mps"
        self.fail_on = fail_on
        self.calls: list[str] = []

    def to(self, device: str) -> _FakeModel:
        self.device = device
        return self

    def __call__(self, _x: object) -> object:
        self.calls.append(self.device)
        if self.device == self.fail_on:
            raise RuntimeError(f"backend {self.device} failed")
        return SimpleNamespace(logits=torch.randn(1, 20, 7))


def test_ppg_retries_on_cpu_when_mps_raises() -> None:
    model = _FakeModel(fail_on="mps")
    ppg = PpgModel(extractor=_FakeExtractor(), model=model, device="mps")

    out = compute_ppg(np.zeros(SR, dtype=np.float32), ppg)

    assert out.shape == (20, 7)
    assert out.dtype == np.float32
    assert np.allclose(out.sum(axis=-1), 1.0, atol=1e-5)  # softmax
    assert model.calls == ["mps", "cpu"]
    assert ppg.device == "cpu"  # các segment sau không thử lại MPS


def test_ppg_after_fallback_stays_on_cpu() -> None:
    model = _FakeModel(fail_on="mps")
    ppg = PpgModel(extractor=_FakeExtractor(), model=model, device="mps")

    compute_ppg(np.zeros(SR, dtype=np.float32), ppg)
    compute_ppg(np.zeros(SR, dtype=np.float32), ppg)

    assert model.calls == ["mps", "cpu", "cpu"]


def test_ppg_error_on_cpu_is_not_swallowed() -> None:
    model = _FakeModel(fail_on="cpu")
    ppg = PpgModel(extractor=_FakeExtractor(), model=model, device="cpu")
    model.device = "cpu"

    with pytest.raises(RuntimeError, match="cpu"):
        compute_ppg(np.zeros(SR, dtype=np.float32), ppg)

    assert model.calls == ["cpu"]  # không thử lại vô ích


def test_ppg_needs_no_fallback_when_mps_works() -> None:
    model = _FakeModel(fail_on=None)
    ppg = PpgModel(extractor=_FakeExtractor(), model=model, device="mps")

    out = compute_ppg(np.zeros(SR, dtype=np.float32), ppg)

    assert out.shape == (20, 7)
    assert model.calls == ["mps"]
    assert ppg.device == "mps"

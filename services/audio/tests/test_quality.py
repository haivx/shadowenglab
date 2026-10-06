"""Test nhãn chất lượng audio (D-09): tỉ lệ công suất no_vocals / vocals và ngưỡng."""

from __future__ import annotations

import numpy as np
import pytest

from audio_service.lesson.quality import (
    MUSIC_THRESHOLD_DB,
    audio_quality_label,
    non_vocal_ratio,
)


def test_threshold_is_the_value_approved_in_01_01_item_7() -> None:
    assert MUSIC_THRESHOLD_DB == -15.0


def test_ratio_is_power_ratio_with_epsilon() -> None:
    vocals = np.array([1.0, -1.0, 1.0, -1.0])
    no_vocals = np.array([0.1, 0.1, -0.1, -0.1])
    expected = np.mean(no_vocals**2) / (np.mean(vocals**2) + 1e-9)
    assert non_vocal_ratio(vocals, no_vocals) == pytest.approx(expected, rel=1e-12)
    assert non_vocal_ratio(vocals, no_vocals) == pytest.approx(0.01, rel=1e-6)


def test_ratio_returns_python_float() -> None:
    assert isinstance(non_vocal_ratio(np.ones(4, dtype=np.float32), np.ones(4, dtype=np.float32)), float)


def test_silence_on_both_stems_is_zero() -> None:
    assert non_vocal_ratio(np.zeros(100), np.zeros(100)) == 0.0


def test_silent_vocals_with_loud_background_is_huge() -> None:
    assert non_vocal_ratio(np.zeros(100), np.ones(100)) > 1e6


def test_float32_input_is_accumulated_in_float64() -> None:
    vocals = np.full(10, 3e19, dtype=np.float32)  # bình phương tràn float32
    no_vocals = np.full(10, 3e19, dtype=np.float32)
    assert non_vocal_ratio(vocals, no_vocals) == pytest.approx(1.0)


def test_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        non_vocal_ratio(np.zeros(10), np.zeros(11))


def test_empty_arrays_raise() -> None:
    with pytest.raises(ValueError):
        non_vocal_ratio(np.zeros(0), np.zeros(0))


def test_label_is_exact_at_the_threshold() -> None:
    t = 10 ** (MUSIC_THRESHOLD_DB / 10)
    assert audio_quality_label(t) == "clean"
    assert audio_quality_label(float(np.nextafter(t, 1.0))) == "music"


def test_label_extremes() -> None:
    assert audio_quality_label(0.0) == "clean"
    assert audio_quality_label(0.5) == "music"
    assert audio_quality_label(1e-5) == "clean"


def test_label_custom_threshold_boundary() -> None:
    t = 10 ** (-10.0 / 10)
    assert audio_quality_label(t, threshold_db=-10.0) == "clean"
    assert audio_quality_label(float(np.nextafter(t, 1.0)), threshold_db=-10.0) == "music"

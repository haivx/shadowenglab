"""Test VAD năng lượng trên tín hiệu tổng hợp (REC-03)."""

from __future__ import annotations

import numpy as np

from audio_service.lesson.vad import is_voiced, voiced_ms

SR = 16000


def _noise(seconds: float, dbfs: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, 1.0, int(SR * seconds))
    x /= np.sqrt(np.mean(x**2))
    return (x * 10 ** (dbfs / 20)).astype(np.float32)


def _tone_burst(total_s: float, start_s: float, burst_s: float, amp: float = 0.3) -> np.ndarray:
    audio = _noise(total_s, -70.0)
    a, b = int(SR * start_s), int(SR * (start_s + burst_s))
    t = np.arange(b - a) / SR
    fade = np.clip(np.minimum(np.arange(b - a), np.arange(b - a)[::-1]) / (0.02 * SR), 0.0, 1.0)
    audio[a:b] += (amp * np.sin(2 * np.pi * 200 * t) * fade).astype(np.float32)
    return audio


def test_digital_silence_is_not_voiced() -> None:
    audio = np.zeros(SR * 2, dtype=np.float32)

    assert not is_voiced(audio)
    assert voiced_ms(audio) == 0


def test_white_noise_at_minus_60_dbfs_is_not_voiced() -> None:
    assert not is_voiced(_noise(2.0, -60.0))


def test_steady_loud_noise_is_not_voiced() -> None:
    """Nền ồn đều (quạt) cao đến đâu cũng không phải tiếng nói: ngưỡng bám theo nền."""
    assert not is_voiced(_noise(2.0, -20.0))


def test_half_second_tone_in_two_seconds_of_low_noise_is_voiced() -> None:
    audio = _tone_burst(2.0, 0.7, 0.5)

    assert is_voiced(audio)
    assert 350 <= voiced_ms(audio) <= 600


def test_sixty_millisecond_click_is_not_voiced() -> None:
    audio = _noise(2.0, -70.0)
    audio[SR : SR + int(0.06 * SR)] = 0.5  # xung 60 ms: không có đoạn liên tục 100 ms

    assert not is_voiced(audio)


def test_empty_and_very_short_input_are_not_voiced() -> None:
    assert not is_voiced(np.zeros(0, dtype=np.float32))
    assert not is_voiced(_tone_burst(0.2, 0.05, 0.1))


def _dense_speech_like(seconds: float = 3.0, dbfs: float = -25.0) -> np.ndarray:
    """Nói liền không có khoảng lặng: tone 150 Hz điều biên 4 Hz (âm tiết), dao động ~12 dB."""
    t = np.arange(int(SR * seconds)) / SR
    envelope = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t))
    x = envelope * np.sin(2 * np.pi * 150 * t)
    x /= np.sqrt(np.mean(x**2))
    return (x * 10 ** (dbfs / 20)).astype(np.float32)


def test_dense_speech_without_any_pause_is_voiced() -> None:
    """03-11: nền ồn phân vị 10 chính là tiếng nói; nhánh tuyệt đối vẫn nhận ra có tiếng."""
    audio = _dense_speech_like()

    assert is_voiced(audio)
    assert voiced_ms(audio) >= 2000


def test_quiet_dense_signal_below_the_absolute_floor_is_not_voiced() -> None:
    assert not is_voiced(_dense_speech_like(dbfs=-55.0))

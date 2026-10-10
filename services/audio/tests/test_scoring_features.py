"""Test feature ngữ điệu (PRO-01): trim, F0 hai lượt, semitone, lọc quãng tám, nội suy, MFCC.

Tín hiệu tổng hợp từ `synth.py`, không audio thật.
"""

from __future__ import annotations

import numpy as np
import parselmouth
from synth import DEFAULT_WORDS, SynthWord, synth_sentence

from audio_service.scoring.features import (
    HOP_S,
    energy_db,
    f0_two_pass,
    interp_smooth,
    mfcc_frames,
    prepare_features,
    to_semitone,
    trim_bounds,
)

SR = 16000


def test_rising_harmonic_glide_gives_rising_semitones() -> None:
    glide = (SynthWord("glide", 1.2, 200.0, 260.0, (700.0, 1200.0)),)
    audio, _ = synth_sentence(glide, lead_s=0.3, tail_s=0.3)

    feats = prepare_features(audio)
    st = feats.f0_st[np.isfinite(feats.f0_st)]

    assert st.size > 100
    assert np.all(np.diff(st) >= -0.25), "smoothing must not leave a falling step"
    assert 3.5 <= st[-1] - st[0] <= 5.5  # 12*log2(260/200) = 4.54 st


def test_a_single_octave_error_frame_is_removed() -> None:
    f0 = np.full(60, 200.0)
    f0[30] = 400.0

    st = to_semitone(f0)

    assert np.isnan(st[30])
    assert np.isfinite(np.delete(st, 30)).all()
    assert abs(float(np.nanmedian(st))) < 1e-9


def test_a_twelve_frame_octave_jump_run_is_removed() -> None:
    """03-11: cụm 120 ms nhảy quãng tám (F0 x2) lọt cửa sổ 9 khung; lượt cửa sổ dài bắt được."""
    f0 = 150.0 * 2 ** (np.sin(np.linspace(0, 3 * np.pi, 300)) * 3 / 12)  # dao động ±3 st
    jump = slice(140, 152)
    f0[jump] *= 2.0

    st = to_semitone(f0)

    assert np.isnan(st[jump]).all()
    assert np.isfinite(np.delete(st, np.arange(140, 152))).all()


def test_a_genuine_eight_semitone_rise_is_kept() -> None:
    """Lên giọng thật 8 st (câu hỏi) không giống quãng tám: giữ nguyên."""
    f0 = np.full(300, 150.0)
    f0[200:240] = 150.0 * 2 ** (8 / 12)

    st = to_semitone(f0)

    assert np.isfinite(st).all()


def test_too_few_voiced_frames_gives_all_nan() -> None:
    f0 = np.zeros(50)
    f0[:4] = 180.0

    assert np.isnan(to_semitone(f0)).all()


def test_short_unvoiced_gap_is_interpolated_and_long_gap_is_not() -> None:
    st = np.concatenate([np.full(20, 1.0), np.full(10, np.nan), np.full(20, 3.0)])
    long_gap = np.concatenate([np.full(20, 1.0), np.full(30, np.nan), np.full(20, 3.0)])

    filled = interp_smooth(st)
    kept = interp_smooth(long_gap)

    assert np.isfinite(filled).all(), "100 ms gap is filled"
    assert np.isnan(kept[20:50]).all(), "300 ms gap stays NaN"
    assert np.isfinite(kept[:20]).all() and np.isfinite(kept[50:]).all()


def test_leading_and_trailing_nan_are_not_extrapolated() -> None:
    st = np.concatenate([np.full(5, np.nan), np.linspace(0, 2, 30), np.full(5, np.nan)])

    out = interp_smooth(st)

    assert np.isnan(out[:5]).all() and np.isnan(out[-5:]).all()


def test_all_zero_input_has_no_voiced_frames_and_does_not_raise() -> None:
    feats = prepare_features(np.zeros(SR, dtype=np.float32))

    assert not feats.voiced.any()
    assert np.isnan(feats.f0_st).all()
    assert feats.mfcc.shape[1] == 12
    assert np.isfinite(feats.mfcc).all()


def test_empty_and_very_short_input_do_not_raise() -> None:
    for audio in (np.zeros(0, dtype=np.float32), np.zeros(300, dtype=np.float32)):
        feats = prepare_features(audio)
        assert len(feats.f0_st) == len(feats.energy_db) == len(feats.mfcc) == len(feats.voiced)


def test_per_frame_arrays_share_the_trimmed_length() -> None:
    audio, _ = synth_sentence(DEFAULT_WORDS)

    feats = prepare_features(audio)
    n = feats.trim_end - feats.trim_start

    assert n > 0
    assert len(feats.f0_st) == len(feats.voiced) == len(feats.energy_db) == len(feats.mfcc) == n
    assert feats.mfcc.shape == (n, 12)
    assert feats.voiced.dtype == bool


def test_mfcc_frame_count_matches_the_energy_grid() -> None:
    audio, _ = synth_sentence(DEFAULT_WORDS)
    n = len(energy_db(audio))

    raw = parselmouth.Sound(audio.astype(np.float64), sampling_frequency=SR).to_mfcc(
        number_of_coefficients=12, window_length=0.025, time_step=HOP_S
    )

    # Praat chỉ đặt khung khi cả cửa sổ 25 ms nằm trong tín hiệu: bớt ~2 khung mỗi đầu so với lưới
    # năng lượng. Đo được 302 so với 306 khung; mfcc_frames đệm biên bằng khung gần nhất.
    assert abs(raw.to_array().shape[1] - n) <= 4
    assert mfcc_frames(audio).shape == (n, 12)


def test_f0_two_pass_stays_inside_the_speaker_range() -> None:
    audio, _ = synth_sentence(DEFAULT_WORDS)

    f0 = f0_two_pass(audio)
    voiced = f0[f0 > 0]

    assert len(f0) == len(energy_db(audio))
    assert voiced.size > 150
    assert voiced.min() > 120.0 and voiced.max() < 300.0


def test_a_soft_tail_is_cut_the_same_way_with_or_without_real_silence() -> None:
    """03-11: ngưỡng cắt tính từ đỉnh ở cả hai phía. Trước đây lặng thật kéo p10 xuống, ngưỡng tụt
    về sàn và đuôi nhỏ của lượt ghi được giữ trong khi bản gốc cắt mất (tỉ lệ độ dài 1.15)."""
    window = np.concatenate([np.full(200, -20.0), np.full(30, -55.0)])
    recording = np.concatenate([np.full(60, -90.0), window, np.full(60, -90.0)])

    margin = 5  # _TRIM_MARGIN_FRAMES

    assert trim_bounds(window)[1] == 200 + margin
    assert trim_bounds(recording)[1] == 60 + 200 + margin


def test_padding_with_silence_trims_to_the_same_length() -> None:
    plain, _ = synth_sentence(DEFAULT_WORDS)
    padded, _ = synth_sentence(DEFAULT_WORDS, lead_s=0.6, tail_s=0.5, seed=1)

    a = prepare_features(plain)
    b = prepare_features(padded)

    assert abs((a.trim_end - a.trim_start) - (b.trim_end - b.trim_start)) <= 3


def test_a_window_with_no_real_silence_keeps_almost_every_frame() -> None:
    audio, _ = synth_sentence(DEFAULT_WORDS, lead_s=0.0, tail_s=0.0, gap_s=0.0)
    n = len(energy_db(audio))

    start, end = trim_bounds(energy_db(audio))

    assert (end - start) >= 0.9 * n


def test_trim_keeps_the_whole_clip_when_nothing_is_above_threshold() -> None:
    assert trim_bounds(np.full(100, -80.0)) == (0, 100)
    assert trim_bounds(np.zeros(0)) == (0, 0)


def test_the_two_sides_use_the_same_function_so_identical_audio_gives_identical_features() -> None:
    audio, _ = synth_sentence(DEFAULT_WORDS)

    a, b = prepare_features(audio), prepare_features(audio.copy())

    assert a.trim_start == b.trim_start and a.trim_end == b.trim_end
    np.testing.assert_array_equal(a.mfcc, b.mfcc)
    np.testing.assert_array_equal(a.f0_st, b.f0_st)

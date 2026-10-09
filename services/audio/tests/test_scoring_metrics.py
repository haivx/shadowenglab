"""Test chỉ số ngữ điệu và các hàm dựng contour/từ (PRO-02, D-04, D-05, D-06)."""

from __future__ import annotations

import numpy as np
import pytest

from audio_service.scoring import metrics
from audio_service.scoring.scorer import RefWord

NAN = float("nan")


def _wave(n: int = 60, amplitude: float = 2.0) -> np.ndarray:
    return amplitude * np.sin(np.linspace(0, 4 * np.pi, n))


# --- melody_match (D-05) ---------------------------------------------------------------------


def test_melody_match_of_a_contour_with_itself_is_one() -> None:
    x = _wave()

    assert metrics.melody_match(x, x) == pytest.approx(1.0)


def test_melody_match_of_a_contour_with_its_negation_is_zero() -> None:
    x = _wave()

    assert metrics.melody_match(x, -x) == 0.0


def test_melody_match_needs_ten_common_voiced_frames() -> None:
    x = _wave()
    sparse = np.full_like(x, np.nan)
    sparse[:9] = x[:9]

    assert metrics.melody_match(x, sparse) == 0.0
    sparse[:10] = x[:10]
    assert metrics.melody_match(x, sparse) > 0.0


def test_melody_match_with_a_constant_side_is_zero() -> None:
    assert metrics.melody_match(_wave(), np.full(60, 1.5)) == 0.0


def test_melody_match_uses_only_frames_finite_on_both_sides() -> None:
    x = _wave()
    y = x.copy()
    y[:20] = np.nan
    x_noisy = x.copy()
    x_noisy[40:] = np.nan

    assert metrics.melody_match(x_noisy, y) == pytest.approx(1.0)


# --- pitch_range -----------------------------------------------------------------------------


def test_pitch_range_is_the_std_ratio_folded_to_at_most_one() -> None:
    x = _wave()

    assert metrics.pitch_range(x, 0.5 * x) == pytest.approx(0.5)
    assert metrics.pitch_range(0.5 * x, x) == pytest.approx(0.5)
    assert metrics.pitch_range(x, x) == pytest.approx(1.0)


def test_pitch_range_with_exactly_one_constant_side_is_zero() -> None:
    assert metrics.pitch_range(_wave(), np.full(60, 0.3)) == 0.0
    assert metrics.pitch_range(np.full(60, 0.3), _wave()) == 0.0


def test_pitch_range_of_two_constant_contours_is_one() -> None:
    assert metrics.pitch_range(np.full(60, 0.3), np.full(60, -2.0)) == 1.0


def test_pitch_range_needs_enough_finite_frames_on_both_sides() -> None:
    few = np.full(60, np.nan)
    few[:9] = _wave()[:9]

    assert metrics.pitch_range(_wave(), few) == 0.0
    assert metrics.pitch_range(few, _wave()) == 0.0


# --- speed -----------------------------------------------------------------------------------


def _db(speech: int, *silences: int) -> np.ndarray:
    """Speech blocks at -20 dB separated by the given silent runs at -90 dB."""
    parts: list[np.ndarray] = []
    for gap in silences:
        parts += [np.full(speech, -20.0), np.full(gap, -90.0)]
    parts.append(np.full(speech, -20.0))
    return np.concatenate(parts)


def test_speech_frames_drops_silent_runs_of_250_ms_or_more_only() -> None:
    short_gap = _db(50, 24)
    long_gap = _db(50, 25)

    assert metrics.speech_frames(short_gap) == 124
    assert metrics.speech_frames(long_gap) == 100


def test_speed_is_the_folded_ratio_of_speech_time() -> None:
    ref = _db(50, 30)
    slow = _db(65, 30)

    assert metrics.speed(ref, ref) == 1.0
    assert metrics.speed(ref, slow) == pytest.approx(100 / 130)
    assert metrics.speed(slow, ref) == pytest.approx(100 / 130)


def test_speed_is_zero_when_either_side_has_no_frames() -> None:
    assert metrics.speed(_db(50), np.zeros(0)) == 0.0
    assert metrics.speed(np.zeros(0), _db(50)) == 0.0


def test_speed_does_not_depend_on_the_signal_level() -> None:
    ref = _db(50, 30)

    assert metrics.speed(ref, ref - 20.0) == 1.0


# --- user_on_ref_axis ------------------------------------------------------------------------


def test_user_on_ref_axis_averages_matched_values_and_leaves_gaps_nan() -> None:
    user = np.array([1.0, 3.0, 5.0, NAN])
    path = np.array([[0, 0], [0, 1], [1, 2], [2, 3], [4, 0]], dtype=np.int64)

    out = metrics.user_on_ref_axis(user, path, 5)

    assert out[0] == pytest.approx(2.0)
    assert out[1] == pytest.approx(5.0)
    assert np.isnan(out[2]), "only NaN matched"
    assert np.isnan(out[3]), "unmatched"
    assert out[4] == pytest.approx(1.0)


def test_user_on_ref_axis_ignores_out_of_range_path_rows() -> None:
    out = metrics.user_on_ref_axis(
        np.array([1.0, 2.0]), np.array([[0, 0], [9, 1], [1, 7]], dtype=np.int64), 3
    )

    assert out[0] == 1.0 and np.isnan(out[1]) and np.isnan(out[2])


def test_user_on_ref_axis_of_an_empty_path_is_all_nan() -> None:
    out = metrics.user_on_ref_axis(np.ones(4), np.zeros((0, 2), dtype=np.int64), 3)

    assert np.isnan(out).all()


# --- contour / words -------------------------------------------------------------------------


def test_contour_points_sample_every_other_frame_round_and_use_none_for_nan() -> None:
    ref = np.array([0.04, 1.26, NAN, 2.0, 3.14159, NAN])
    user = np.array([NAN, 1.0, 2.0, 3.0, 4.0, 5.0])

    ref_pts, user_pts = metrics.contour_points(ref, user)

    assert ref_pts == [0.0, None, 3.1]
    assert user_pts == [None, 2.0, 4.0]


def test_word_frames_shift_by_the_trim_and_clip_to_the_axis() -> None:
    words = [RefWord("a", 0.20, 0.50), RefWord("b", 0.50, 0.90), RefWord("c", 2.0, 3.0)]

    frames = metrics.word_frames(words, trim_start=10, n_ref=80)

    assert frames == [(10, 40), (40, 80), (80, 80)]


def test_word_frames_never_go_negative_before_the_trim() -> None:
    frames = metrics.word_frames([RefWord("a", 0.0, 0.05)], trim_start=20, n_ref=50)

    assert frames == [(0, 0)]


def test_word_bounds_are_strictly_increasing_even_when_words_share_a_frame() -> None:
    frames = [(0, 5), (0, 9), (1, 4), (30, 40)]

    bounds = metrics.word_bounds(frames, step=2, length=50)

    assert bounds == [0, 1, 2, 15]
    assert all(b < a for b, a in zip(bounds, bounds[1:], strict=False))


def test_word_bounds_stay_below_the_contour_length() -> None:
    frames = [(10, 20), (96, 98), (99, 100), (100, 100)]

    bounds = metrics.word_bounds(frames, step=2, length=50)

    assert bounds[-1] <= 49
    assert all(b < a for b, a in zip(bounds, bounds[1:], strict=False))
    assert all(b >= 0 for b in bounds)


# --- word_similarity (03-01 mục G) -----------------------------------------------------------


def test_word_similarity_is_one_for_identical_contours() -> None:
    x = _wave(40)

    assert metrics.word_similarity(x, x, [(0, 20), (20, 40)], 0.0, 0.3) == [
        pytest.approx(1.0),
        pytest.approx(1.0),
    ]


def test_word_similarity_removes_the_sentence_offset() -> None:
    x = _wave(40)

    sims = metrics.word_similarity(x, x + 4.0, [(0, 40)], offset=4.0, melody=0.0)

    assert sims == [pytest.approx(1.0)]


def test_word_similarity_reaches_zero_at_six_semitones_rms() -> None:
    x = np.zeros(40)

    assert metrics.word_similarity(x, x + 6.0, [(0, 40)], 0.0, 1.0) == [pytest.approx(0.0)]
    assert metrics.word_similarity(x, x + 3.0, [(0, 40)], 0.0, 1.0) == [pytest.approx(0.5)]
    assert metrics.word_similarity(x, x + 12.0, [(0, 40)], 0.0, 1.0) == [pytest.approx(0.0)]


def test_word_similarity_falls_back_to_melody_with_fewer_than_five_common_frames() -> None:
    ref = np.zeros(40)
    user = np.full(40, np.nan)
    user[:4] = 0.0

    assert metrics.word_similarity(ref, user, [(0, 10)], 0.0, 0.42) == [0.42]


def test_sentence_offset_is_the_median_difference() -> None:
    ref = np.zeros(30)
    user = np.full(30, 2.0)
    user[0] = 100.0

    assert metrics.sentence_offset(ref, user) == pytest.approx(2.0)
    assert metrics.sentence_offset(ref, np.full(30, np.nan)) == 0.0


# --- ref_frame_to_user_seconds ---------------------------------------------------------------


def test_ref_frame_maps_to_user_seconds_through_the_path_with_the_trim_offset() -> None:
    path = np.array([[0, 0], [1, 2], [2, 3], [3, 3]], dtype=np.int64)

    assert metrics.ref_frame_to_user_seconds(1, path, 10) == pytest.approx(0.12)
    assert metrics.ref_frame_to_user_seconds(3, path, 0) == pytest.approx(0.03)
    assert metrics.ref_frame_to_user_seconds(99, path, 0) == pytest.approx(0.03), "clamped"
    assert metrics.ref_frame_to_user_seconds(1, np.zeros((0, 2), dtype=np.int64), 5) == 0.0

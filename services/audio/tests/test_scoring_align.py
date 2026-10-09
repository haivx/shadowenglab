"""Test căn thời gian MFCC (D-01, D-02, T-03-05)."""

from __future__ import annotations

import numpy as np
import pytest
from synth import DEFAULT_WORDS, synth_sentence

from audio_service.scoring import align as align_module
from audio_service.scoring.align import (
    Alignment,
    align,
    dtw_slack,
    linear_path,
    pairwise_dist,
)
from audio_service.scoring.features import prepare_features
from audio_service.scoring.thresholds import ALIGN_RATIO_MAX, ALIGN_RATIO_MIN


@pytest.fixture(scope="module")
def mfcc() -> np.ndarray:
    audio, _ = synth_sentence(DEFAULT_WORDS)
    return prepare_features(audio).mfcc


def _assert_monotonic(path: np.ndarray) -> None:
    assert (np.diff(path[:, 0]) >= 0).all()
    assert (np.diff(path[:, 1]) >= 0).all()


def test_identical_inputs_give_the_diagonal_with_zero_cost(mfcc: np.ndarray) -> None:
    result = align(mfcc, mfcc)

    assert result.ok and not result.linear
    assert result.cost <= 1e-9
    assert result.ratio == pytest.approx(1.0)
    n = len(mfcc)
    np.testing.assert_array_equal(result.path[:, 0], np.arange(n))
    np.testing.assert_array_equal(result.path[:, 1], np.arange(n))


def test_a_stretched_copy_is_aligned_with_a_monotonic_path() -> None:
    ref, _ = synth_sentence(DEFAULT_WORDS)
    slow, _ = synth_sentence(DEFAULT_WORDS, dur_scale=1.3, seed=2)
    ref_m, slow_m = prepare_features(ref).mfcc, prepare_features(slow).mfcc

    result = align(ref_m, slow_m)

    assert result.ok and not result.linear
    assert result.path.shape[0] == len(ref_m), "path covers every reference frame"
    _assert_monotonic(result.path)
    assert result.path[-1, 1] > 0.8 * len(slow_m)


def test_length_ratio_outside_range_returns_a_linear_path_and_never_builds_a_matrix(
    mfcc: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("no cost matrix for a ratio outside the range")

    monkeypatch.setattr(align_module, "pairwise_dist", forbidden)
    monkeypatch.setattr(align_module, "dtw_slack", forbidden)
    long_user = np.tile(mfcc, (3, 1))[: int(len(mfcc) * 2.5)]

    result = align(mfcc, long_user)

    assert result.linear and not result.ok
    assert result.ratio == pytest.approx(2.5, abs=0.01)
    assert result.ratio > ALIGN_RATIO_MAX
    assert result.path.shape == (len(mfcc), 2)
    assert np.isinf(result.cost)
    _assert_monotonic(result.path)


def test_too_short_user_is_also_linear(mfcc: np.ndarray) -> None:
    short_user = mfcc[: int(len(mfcc) * 0.4)]

    result = align(mfcc, short_user)

    assert result.ratio < ALIGN_RATIO_MIN
    assert result.linear and not result.ok
    assert result.path.shape[0] == len(mfcc)


def test_unrelated_features_are_not_ok_but_keep_the_measured_cost() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(size=(120, 12))
    user = rng.normal(size=(130, 12))

    result = align(ref, user)

    assert not result.ok and result.linear
    assert np.isfinite(result.cost) and result.cost > 1.1
    assert result.path.shape == (120, 2)


def test_empty_and_single_frame_inputs_do_not_raise() -> None:
    empty = np.zeros((0, 12))
    one = np.zeros((1, 12))
    many = np.zeros((20, 12))

    assert align(empty, many).path.shape == (0, 2)
    assert align(many, empty).path.shape == (0, 2)
    assert not align(one, many).ok
    assert not align(many, one).ok


def test_linear_path_maps_the_ends_and_is_monotonic() -> None:
    path = linear_path(11, 21)

    np.testing.assert_array_equal(path[:, 0], np.arange(11))
    assert path[0, 1] == 0 and path[-1, 1] == 20
    _assert_monotonic(path)
    assert linear_path(1, 5).tolist() == [[0, 0]]
    assert linear_path(0, 5).shape == (0, 2)
    assert linear_path(5, 0).shape == (0, 2)


def test_dtw_without_a_feasible_path_returns_empty_and_inf() -> None:
    cost = np.ones((10, 60))

    path, total = dtw_slack(cost, slack=5)

    assert path.shape == (0, 2)
    assert np.isinf(total)


def test_pairwise_dist_matches_brute_force() -> None:
    rng = np.random.default_rng(1)
    a, b = rng.normal(size=(7, 12)), rng.normal(size=(9, 12))

    expected = np.array([[np.linalg.norm(x - y) for y in b] for x in a]) / np.sqrt(12)

    np.testing.assert_allclose(pairwise_dist(a, b), expected, atol=1e-9)


def test_alignment_is_a_frozen_dataclass() -> None:
    result = Alignment(np.zeros((0, 2), dtype=np.int64), 0.0, 1.0, True, False)

    with pytest.raises(AttributeError):
        result.ok = False  # type: ignore[misc]

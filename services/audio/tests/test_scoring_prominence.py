"""Prominence từng từ, ghép khung người học qua path và ngắt nghỉ (03-06, PRO-02, Lớp B)."""

from __future__ import annotations

import numpy as np
import pytest

from audio_service.scoring.align import linear_path
from audio_service.scoring.prominence import (
    ms_to_frames,
    pause_entries,
    ref_row_at_user_frame,
    silent_runs,
    stress_entries,
    user_word_frames,
    word_prominence,
)

FRAMES = [(0, 20), (20, 50), (50, 70), (70, 100)]


def _contour() -> tuple[np.ndarray, np.ndarray]:
    st = np.zeros(100)
    db = np.full(100, -30.0)
    st[0:20], db[0:20] = np.linspace(0, 2, 20), -20.0
    st[20:50], db[20:50] = np.linspace(0, 6, 30), -10.0  # từ 1: cao, to, dài
    st[50:70], db[50:70] = np.linspace(0, 1, 20), -25.0
    st[70:100], db[70:100] = np.linspace(0, 3, 30), -15.0
    return st, db


def test_prominence_follows_the_product_formula() -> None:
    st, db = _contour()
    f0_max = np.array([2.0, 6.0, 1.0, 3.0])
    db_max = np.array([-20.0, -10.0, -25.0, -15.0])
    length = np.array([20.0, 30.0, 20.0, 30.0])

    def z(x: np.ndarray) -> np.ndarray:
        return (x - x.mean()) / x.std()

    expected = 0.4 * z(f0_max) + 0.4 * z(db_max) + 0.2 * z(length)

    assert word_prominence(st, db, FRAMES) == pytest.approx(expected)


def test_prominence_is_a_z_score_so_it_sums_to_zero_across_words() -> None:
    st, db = _contour()

    assert float(word_prominence(st, db, FRAMES).sum()) == pytest.approx(0.0, abs=1e-9)


def test_a_word_with_fewer_than_three_voiced_frames_is_nan_and_excluded_from_the_z_scores() -> None:
    st, db = _contour()
    st[50:70] = np.nan
    st[52:54] = 1.0  # chỉ còn 2 khung hữu hạn

    prom = word_prominence(st, db, FRAMES)

    assert np.isnan(prom[2])
    assert np.isfinite(prom[[0, 1, 3]]).all()
    assert float(np.nansum(prom)) == pytest.approx(0.0, abs=1e-9)


def test_prominence_is_nan_for_empty_or_out_of_range_words() -> None:
    st, db = _contour()

    prom = word_prominence(st, db, [(0, 0), (90, 90), (200, 210), (20, 50)])

    assert np.isnan(prom[:3]).all()
    assert prom[3] == pytest.approx(0.0)  # một từ duy nhất: std = 0 nên z = 0


def test_stress_entries_write_nan_as_zero() -> None:
    nan = float("nan")
    entries = stress_entries(
        ["a", "b", "c"], np.array([1.0, nan, -0.5]), np.array([nan, 2.0, 0.25])
    )

    assert entries == [
        {"word": "a", "ref": 1.0, "user": 0.0},
        {"word": "b", "ref": 0.0, "user": 2.0},
        {"word": "c", "ref": -0.5, "user": 0.25},
    ]


def test_user_word_frames_follow_the_path() -> None:
    path = np.stack([np.arange(100), np.arange(100) * 2], axis=1).astype(np.int64)  # nói chậm x2

    assert user_word_frames(FRAMES, path, 200) == [(0, 39), (40, 99), (100, 139), (140, 199)]
    assert user_word_frames(FRAMES, np.zeros((0, 2), dtype=np.int64), 200) == [(0, 0)] * 4
    assert user_word_frames([(30, 30)], path, 200) == [(0, 0)]


def test_silent_runs_use_a_relative_mask_and_a_minimum_length() -> None:
    db = np.full(100, -10.0)
    db[20:50] = -80.0
    db[60:70] = -80.0

    assert silent_runs(db, 25) == [(20, 50)]
    assert silent_runs(db, 10) == [(20, 50), (60, 70)]
    assert silent_runs(db - 25.0, 25) == [(20, 50)], "mặt nạ tương đối: bất biến theo mức tín hiệu"
    assert silent_runs(np.zeros(0), 5) == []


def test_ref_row_at_user_frame_takes_the_median_row_or_the_nearest_column() -> None:
    path = np.array([[0, 0], [1, 1], [2, 1], [3, 1], [4, 3]], dtype=np.int64)

    assert ref_row_at_user_frame(path, 1) == 2.0
    assert ref_row_at_user_frame(path, 2) in (3.0, 4.0)  # cột 2 bị bước (1, 2) bỏ qua
    assert np.isnan(ref_row_at_user_frame(np.zeros((0, 2), dtype=np.int64), 0))


def test_ms_to_frames() -> None:
    assert ms_to_frames(250) == 25
    assert ms_to_frames(100) == 10


def _gap_db(n: int, words: list[tuple[int, int]], silent_gap: tuple[int, int] | None) -> np.ndarray:
    db = np.full(n, -80.0)
    for start, end in words:
        db[start:end] = 0.0
    if silent_gap is not None:
        db[silent_gap[0] : silent_gap[1]] = -80.0
    return db


def test_pause_entries_list_gaps_of_at_least_100_ms_on_either_side() -> None:
    words = [(10, 50), (53, 93), (110, 150)]  # khe 0: 3 khung, khe 1: 17 khung (170 ms)
    ref_db = _gap_db(160, words, None)
    path = linear_path(160, 160)

    entries = pause_entries(ref_db, ref_db, words, path)

    assert entries == [{"afterWord": 1, "refMs": 170.0, "userMs": 170.0}]


def test_pause_entries_report_a_user_only_pause_through_the_path() -> None:
    words = [(10, 50), (53, 93), (96, 136)]
    ref_db = _gap_db(150, words, None)
    extra = 30
    at_row = 51
    user_db = np.concatenate([ref_db[: at_row + 1], np.full(extra, -80.0), ref_db[at_row + 1 :]])
    rows = np.concatenate([np.arange(150), np.full(extra, at_row)])
    order = np.argsort(rows, kind="stable")
    path = np.stack([rows[order], np.arange(150 + extra)], axis=1).astype(np.int64)

    entries = pause_entries(ref_db, user_db, words, path)

    assert len(entries) == 1
    assert entries[0]["afterWord"] == 0
    assert entries[0]["refMs"] == 30.0
    assert entries[0]["userMs"] >= 300.0


def test_pause_entries_are_empty_without_gaps_or_with_an_empty_path() -> None:
    db = np.full(50, -10.0)

    assert pause_entries(db, db, [(0, 50)], linear_path(50, 50)) == []
    assert pause_entries(db, db, [(0, 20), (20, 50)], np.zeros((0, 2), dtype=np.int64)) == []

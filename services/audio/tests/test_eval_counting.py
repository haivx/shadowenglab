"""Cách đếm TP/FP/FN của eval nội bộ (04-02 Task 2, D-07, D-08, D-09, D-10, D-11b, D-18b).

Thuần: `Observation` dựng tay, không audio. Mỗi dòng của bảng mã C (04-01) và các quy tắc C1, C2,
C4 có ít nhất một test. Giá trị cuối của bảng nằm ở 04-01-SUMMARY, không ở plan 04-02.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

import pytest
from eval_synth import load_evalkit

WORDS = ("alpha", "bravo", "charlie", "delta", "echo")


@pytest.fixture
def counting(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("counting", monkeypatch)


def issue(code: str, word: int | None = None, **data: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"code": code, "data": data}
    if word is not None:
        out["wordIndex"] = word
    return out


def stress(user_word: int, ref_word: int = 0) -> dict[str, Any]:
    return issue("STRESS_MISMATCH", ref_word, refWord=WORDS[ref_word], userWord=WORDS[user_word])


def obs(
    counting: ModuleType,
    *,
    source: str = "error",
    error_type: str | None = None,
    word_index: int | None = None,
    issues: tuple[dict[str, Any], ...] = (),
    also: tuple[tuple[str, int | None], ...] = (),
    align_ok: bool = True,
    voiced: bool = True,
    lesson_id: str = "L1",
) -> Any:
    return counting.Observation(
        source=source,
        split="tuning",
        lesson_id=lesson_id,
        segment_index=0,
        case_id="c0001" if source != "self" else None,
        clip="clip" if source != "self" else None,
        error_type=error_type,
        word_index=word_index,
        also_present=also,
        words=WORDS,
        issues=issues,
        align_ok=align_ok,
        voiced=voiced,
        overall=0.8,
    )


def outcomes(counting: ModuleType, observation: Any) -> list[tuple[str, int | None, str]]:
    return [(v.code, v.word_index, v.outcome) for v in counting.classify(observation)]


# --- wrong_stress (B1-a: so chữ userWord với từ khai báo) -------------------------------------


def test_wrong_stress_is_a_tp_when_the_user_word_is_the_declared_word(counting: ModuleType) -> None:
    case = obs(counting, error_type="wrong_stress", word_index=3, issues=(stress(3),))

    assert outcomes(counting, case) == [("STRESS_MISMATCH", 0, "tp")]


def test_wrong_stress_on_another_word_is_a_fp(counting: ModuleType) -> None:
    case = obs(counting, error_type="wrong_stress", word_index=3, issues=(stress(1),))

    assert outcomes(counting, case) == [("STRESS_MISMATCH", 0, "fp")]


def test_wrong_stress_pitch_deviation_on_the_word_is_secondary_elsewhere_fp(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="wrong_stress",
        word_index=3,
        issues=(issue("PITCH_DEVIATION", 3), issue("PITCH_DEVIATION", 2)),
    )

    assert outcomes(counting, case) == [
        ("PITCH_DEVIATION", 3, "secondary"),
        ("PITCH_DEVIATION", 2, "fp"),
    ]


# --- extra_pause (D-08: lệch +-1 từ; C1: tối đa một TP) -------------------------------------


@pytest.mark.parametrize("word", [1, 2, 3])
def test_extra_pause_within_one_word_is_a_tp(counting: ModuleType, word: int) -> None:
    case = obs(
        counting, error_type="extra_pause", word_index=2, issues=(issue("EXTRA_PAUSE", word),)
    )

    assert outcomes(counting, case) == [("EXTRA_PAUSE", word, "tp")]


def test_extra_pause_two_words_away_is_a_fp(counting: ModuleType) -> None:
    case = obs(counting, error_type="extra_pause", word_index=2, issues=(issue("EXTRA_PAUSE", 4),))

    assert outcomes(counting, case) == [("EXTRA_PAUSE", 4, "fp")]


def test_c1_the_nearest_pause_is_the_tp_and_the_other_in_range_is_a_fp(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="extra_pause",
        word_index=2,
        issues=(issue("EXTRA_PAUSE", 2), issue("EXTRA_PAUSE", 3)),
    )

    assert outcomes(counting, case) == [("EXTRA_PAUSE", 2, "tp"), ("EXTRA_PAUSE", 3, "fp")]


def test_c1_a_tie_in_distance_goes_to_the_smaller_word_index(counting: ModuleType) -> None:
    case = obs(
        counting,
        error_type="extra_pause",
        word_index=2,
        issues=(issue("EXTRA_PAUSE", 3), issue("EXTRA_PAUSE", 1)),
    )

    assert outcomes(counting, case) == [("EXTRA_PAUSE", 3, "fp"), ("EXTRA_PAUSE", 1, "tp")]


# --- flat -------------------------------------------------------------------------------------


def test_flat_pitch_is_the_tp_pitch_deviation_anywhere_is_secondary_stress_is_a_fp(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="flat",
        issues=(stress(1), issue("PITCH_DEVIATION", 4), issue("FLAT_PITCH")),
    )

    assert outcomes(counting, case) == [
        ("STRESS_MISMATCH", 0, "fp"),
        ("PITCH_DEVIATION", 4, "secondary"),
        ("FLAT_PITCH", None, "tp"),
    ]


# --- final_rise -------------------------------------------------------------------------------


def test_final_rise_final_contour_is_tp_last_word_pitch_deviation_secondary_other_fp(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="final_rise",
        issues=(
            issue("FINAL_CONTOUR"),
            issue("PITCH_DEVIATION", 4),
            issue("PITCH_DEVIATION", 2),
        ),
    )

    assert outcomes(counting, case) == [
        ("FINAL_CONTOUR", None, "tp"),
        ("PITCH_DEVIATION", 4, "secondary"),
        ("PITCH_DEVIATION", 2, "fp"),
    ]


# --- pitch_off --------------------------------------------------------------------------------


def test_pitch_off_is_a_tp_on_the_declared_word_and_a_fp_on_another(counting: ModuleType) -> None:
    case = obs(
        counting,
        error_type="pitch_off",
        word_index=1,
        issues=(issue("PITCH_DEVIATION", 1), issue("PITCH_DEVIATION", 2)),
    )

    assert outcomes(counting, case) == [
        ("PITCH_DEVIATION", 1, "tp"),
        ("PITCH_DEVIATION", 2, "fp"),
    ]


def test_pitch_off_stress_mismatch_whose_user_word_is_the_word_is_secondary(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="pitch_off",
        word_index=1,
        issues=(stress(1, ref_word=3), stress(2, ref_word=3)),
    )

    assert outcomes(counting, case) == [
        ("STRESS_MISMATCH", 3, "secondary"),
        ("STRESS_MISMATCH", 3, "fp"),
    ]


# --- D-07, D-18b: không có mã chính, hoặc âm tính ------------------------------------------------


@pytest.mark.parametrize("error_type", ["weak_form", "final_drop"])
def test_d07_every_layer_c_issue_on_a_phase5_clip_is_a_fp_and_nothing_is_expected(
    counting: ModuleType, error_type: str
) -> None:
    case = obs(
        counting,
        error_type=error_type,
        word_index=2,
        issues=(issue("PITCH_DEVIATION", 2), issue("EXTRA_PAUSE", 2), issue("FLAT_PITCH")),
    )

    assert [v.outcome for v in counting.classify(case)] == ["fp", "fp", "fp"]
    tallies = counting.tally([case])
    assert all(tallies[code].expected == 0 for code in counting.LAYER_C_CODES)
    assert tallies[counting.POOLED].fp == 3


@pytest.mark.parametrize("source", ["correct", "self"])
def test_d18_every_issue_on_a_correct_clip_or_the_self_compare_is_a_fp(
    counting: ModuleType, source: str
) -> None:
    case = obs(counting, source=source, issues=(issue("FLAT_PITCH"), issue("EXTRA_PAUSE", 1)))

    assert [v.outcome for v in counting.classify(case)] == ["fp", "fp"]


# --- C2: alsoPresent là trung tính ----------------------------------------------------------------


def test_c2_an_also_present_pause_near_its_word_is_neutral_elsewhere_a_fp(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="pitch_off",
        word_index=1,
        also=(("extra_pause", 4),),
        issues=(
            issue("EXTRA_PAUSE", 4),
            issue("EXTRA_PAUSE", 3),
            issue("EXTRA_PAUSE", 0),
        ),
    )

    assert outcomes(counting, case) == [
        ("EXTRA_PAUSE", 4, "also"),
        ("EXTRA_PAUSE", 3, "also"),
        ("EXTRA_PAUSE", 0, "fp"),
    ]


def test_c2_also_present_covers_the_secondary_codes_of_its_error_type(
    counting: ModuleType,
) -> None:
    case = obs(
        counting,
        error_type="pitch_off",
        word_index=1,
        also=(("flat", None),),
        issues=(issue("FLAT_PITCH"), issue("PITCH_DEVIATION", 3)),
    )

    assert outcomes(counting, case) == [
        ("FLAT_PITCH", None, "also"),
        ("PITCH_DEVIATION", 3, "also"),
    ]


# --- C4, D-11b: FN, căn thất bại, recall ----------------------------------------------------------


def test_a_flat_case_without_any_issue_is_a_false_negative(counting: ModuleType) -> None:
    tallies = counting.tally([obs(counting, error_type="flat")])

    assert (tallies["FLAT_PITCH"].found, tallies["FLAT_PITCH"].expected) == (0, 1)
    assert tallies["FLAT_PITCH"].tp == 0 and tallies["FLAT_PITCH"].fp == 0


def test_c4_recall_counts_cases_with_a_tp_over_cases_with_the_primary_code(
    counting: ModuleType,
) -> None:
    hit = obs(counting, error_type="extra_pause", word_index=2, issues=(issue("EXTRA_PAUSE", 3),))
    miss = obs(counting, error_type="extra_pause", word_index=2)
    wrong = obs(counting, error_type="extra_pause", word_index=2, issues=(issue("EXTRA_PAUSE", 4),))

    tallies = counting.tally([hit, miss, wrong])

    row = tallies["EXTRA_PAUSE"]
    assert (row.found, row.expected, row.tp, row.fp) == (1, 3, 1, 1)


def test_d11b_a_failed_alignment_on_a_word_level_case_is_a_fn_and_a_row_in_the_failure_table(
    counting: ModuleType,
) -> None:
    failed = obs(counting, error_type="extra_pause", word_index=2, align_ok=False)
    fine = obs(counting, error_type="extra_pause", word_index=2, issues=(issue("EXTRA_PAUSE", 2),))

    tallies = counting.tally([failed, fine])
    failures = counting.align_failures([failed, fine])

    assert (tallies["EXTRA_PAUSE"].found, tallies["EXTRA_PAUSE"].expected) == (1, 2)
    assert failures[("L1", "extra_pause")] == (1, 2)


def test_align_failures_are_keyed_by_lesson_and_label_for_correct_and_self_too(
    counting: ModuleType,
) -> None:
    rows = [
        obs(counting, source="correct", lesson_id="L2"),
        obs(counting, source="self", lesson_id="L2", align_ok=False),
        obs(counting, error_type="flat", lesson_id="L2"),
    ]

    failures = counting.align_failures(rows)

    assert failures == {("L2", "correct"): (0, 1), ("L2", "self"): (1, 1), ("L2", "flat"): (0, 1)}


def test_a_clip_without_speech_has_no_issue_and_is_a_fn(counting: ModuleType) -> None:
    silent = obs(counting, error_type="flat", voiced=False, align_ok=False)

    tallies = counting.tally([silent])

    assert (tallies["FLAT_PITCH"].found, tallies["FLAT_PITCH"].expected) == (0, 1)


def test_pooled_precision_sums_tp_and_fp_over_the_layer_c_codes(counting: ModuleType) -> None:
    rows = [
        obs(counting, error_type="flat", issues=(issue("FLAT_PITCH"),)),
        obs(counting, source="correct", issues=(issue("EXTRA_PAUSE", 1),)),
        obs(counting, error_type="pitch_off", word_index=1, issues=(issue("PITCH_DEVIATION", 1),)),
    ]

    tallies = counting.tally(rows)

    pooled = tallies[counting.POOLED]
    assert (pooled.tp, pooled.fp) == (2, 1)
    assert (pooled.found, pooled.expected) == (2, 2)


def test_code_table_covers_the_seven_error_types(counting: ModuleType) -> None:
    assert set(counting.CODE_TABLE) == {
        "wrong_stress",
        "flat",
        "extra_pause",
        "final_rise",
        "pitch_off",
        "weak_form",
        "final_drop",
    }


# --- Wilson -----------------------------------------------------------------------------------


def test_wilson_interval_matches_the_published_value(counting: ModuleType) -> None:
    low, high = counting.wilson(9, 10)

    assert low == pytest.approx(0.596, abs=0.001)
    assert high == pytest.approx(0.982, abs=0.001)


def test_wilson_upper_bound_is_exactly_one_when_all_succeed_and_none_when_empty(
    counting: ModuleType,
) -> None:
    assert counting.wilson(5, 5)[1] == 1.0
    assert counting.wilson(0, 5)[0] == 0.0
    assert counting.wilson(0, 0) is None

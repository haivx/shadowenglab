"""Cờ bật/tắt rule Lớp C (04-05, D-15, 04-01 mục H).

`run_rules` bỏ hẳn lời gọi của rule có cờ `False`: không issue, nên không tip; thứ tự các rule còn
lại (nền của `issueRef`) giữ nguyên. Mặc định cả năm cờ `True` và hành vi không đổi (các test chấm
cũ pass không sửa). Hàm rule riêng lẻ vẫn chạy khi gọi trực tiếp: chỉ `run_rules` bị chặn.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from synth import DEFAULT_WORDS, synth_sentence
from test_scoring_rules import _crafted, _paused, _prom, _raised, _wave

from audio_service.rules import engine
from audio_service.scoring import thresholds
from audio_service.scoring.features import prepare_features
from audio_service.scoring.scorer import RefWord, score_prosody, to_score_result

FLAGS = (
    "STRESS_MISMATCH_ENABLED",
    "FINAL_CONTOUR_ENABLED",
    "EXTRA_PAUSE_ENABLED",
    "PITCH_DEVIATION_ENABLED",
    "FLAT_PITCH_ENABLED",
)
ALL_CODES = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")


def _flat_score() -> object:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    words = [RefWord(text=t, start_s=s, end_s=e) for t, s, e in marks]
    return score_prosody(prepare_features(audio), prepare_features(flat), words)


def _three_rule_input() -> engine.RuleInput:
    """Đầu vào dựng tay có STRESS_MISMATCH, EXTRA_PAUSE (sau từ 0) và PITCH_DEVIATION (từ 3)."""
    base = _paused(at_row=51, extra=30)
    return replace(
        base,
        ref_prominence=_prom(0.0, 2.0, 0.5, 0.0, -1.0),
        user_prominence=_prom(0.0, 0.3, 0.2, 1.9, -1.0),
        user_st_on_ref=_raised(4.0, 139, 179),
        ref=replace(base.ref, f0_st=_wave()),
    )


def _codes(inp: engine.RuleInput) -> list[tuple[str, int | None]]:
    return [(r.issue["code"], r.issue.get("wordIndex")) for r in engine.run_rules(inp)]


def test_all_five_flags_default_to_true_and_the_version_does_not_move() -> None:
    for flag in FLAGS:
        assert getattr(thresholds, flag) is True, flag
    assert thresholds.THRESHOLDS_VERSION == "p2-1"  # thêm cờ không đổi hành vi (04-01 mục H)


def test_enabled_codes_lists_every_rule_in_the_fixed_order_by_default() -> None:
    assert engine.enabled_codes() == ALL_CODES


@pytest.mark.parametrize("code", ALL_CODES)
def test_a_disabled_rule_leaves_enabled_codes_without_it_and_keeps_the_order(
    code: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine, f"{code}_ENABLED", False)

    assert engine.enabled_codes() == tuple(c for c in ALL_CODES if c != code)


def test_default_flags_keep_all_three_rules_of_the_hand_built_input_in_order() -> None:
    assert _codes(_three_rule_input()) == [
        ("STRESS_MISMATCH", 1),
        ("EXTRA_PAUSE", 0),
        ("PITCH_DEVIATION", 3),
    ]


def test_disabling_extra_pause_keeps_the_other_rules_in_their_fixed_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "EXTRA_PAUSE_ENABLED", False)

    assert _codes(_three_rule_input()) == [("STRESS_MISMATCH", 1), ("PITCH_DEVIATION", 3)]


@pytest.mark.parametrize(
    ("flag", "gone"),
    [
        ("STRESS_MISMATCH_ENABLED", "STRESS_MISMATCH"),
        ("PITCH_DEVIATION_ENABLED", "PITCH_DEVIATION"),
    ],
)
def test_a_disabled_rule_never_appears_in_run_rules(
    flag: str, gone: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine, flag, False)

    assert gone not in [code for code, _ in _codes(_three_rule_input())]


def test_disabled_rules_are_not_called_at_all(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def spy(name: str, result: object) -> object:
        def rule(inp: engine.RuleInput) -> object:
            called.append(name)
            return result

        return rule

    monkeypatch.setattr(engine, "stress_mismatch", spy("stress", None))
    monkeypatch.setattr(engine, "final_contour", spy("final", None))
    monkeypatch.setattr(engine, "extra_pause", spy("pause", []))
    monkeypatch.setattr(engine, "pitch_deviation", spy("pitch", []))
    monkeypatch.setattr(engine, "flat_pitch", spy("flat", None))
    for flag in FLAGS:
        monkeypatch.setattr(engine, flag, False)
    monkeypatch.setattr(engine, "EXTRA_PAUSE_ENABLED", True)

    engine.run_rules(_crafted())

    assert called == ["pause"]


def test_a_disabled_flat_pitch_rule_yields_no_issue_and_no_tip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "FLAT_PITCH_ENABLED", False)

    score = _flat_score()
    result = to_score_result(
        score,  # type: ignore[arg-type]
        lesson_id="01TESTLESSON",
        segment_index=0,
        attempt=1,
        timing_ms={"rules": 1.0},
    )

    assert "FLAT_PITCH" not in [i.root.code for i in result.issues]
    assert result.tips == []
    assert engine.enabled_codes() == ALL_CODES[:-1]


def test_the_default_flat_learner_still_gets_its_issue_and_tip() -> None:
    score = _flat_score()
    result = to_score_result(
        score,  # type: ignore[arg-type]
        lesson_id="01TESTLESSON",
        segment_index=0,
        attempt=1,
        timing_ms={"rules": 1.0},
    )

    assert [i.root.code for i in result.issues] == ["FLAT_PITCH"]
    assert len(result.tips) == 1


def test_rule_functions_still_fire_when_called_directly_with_their_flag_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for flag in FLAGS:
        monkeypatch.setattr(engine, flag, False)
    inp = _three_rule_input()

    assert engine.run_rules(inp) == []
    assert engine.stress_mismatch(inp) is not None
    assert [r.issue["wordIndex"] for r in engine.extra_pause(inp)] == [0]
    assert [r.issue["wordIndex"] for r in engine.pitch_deviation(inp)] == [3]

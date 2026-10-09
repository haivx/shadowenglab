"""Tip template tiếng Việt và chọn tip theo D-14 (03-06, RUL-02)."""

from __future__ import annotations

from typing import Any

import pytest
from synth import DEFAULT_WORDS, synth_sentence

from audio_service.contracts_gen import ScoreResult
from audio_service.rules.engine import RuleIssue
from audio_service.rules.tips import PRIORITY, render_tip, select_tips
from audio_service.scoring.features import prepare_features
from audio_service.scoring.scorer import RefWord, score_prosody, to_score_result

WORDS = ["The", "Brown", "bravo", "fox", "out"]


def _stress(ref_word: str, user_word: str, *, index: int = 1, severity: float = 1.0) -> RuleIssue:
    data = {"refWord": ref_word, "userWord": user_word}
    return RuleIssue({"code": "STRESS_MISMATCH", "wordIndex": index, "data": data}, severity)


def _pause(index: int, user_ms: float, *, severity: float | None = None) -> RuleIssue:
    data = {"refMs": 30.0, "userMs": user_ms}
    issue = {"code": "EXTRA_PAUSE", "wordIndex": index, "data": data}
    return RuleIssue(issue, user_ms if severity is None else severity)


def _final(ref_slope: float, user_slope: float) -> RuleIssue:
    data = {"refSlope": ref_slope, "userSlope": user_slope}
    return RuleIssue({"code": "FINAL_CONTOUR", "data": data}, abs(user_slope - ref_slope))


def _deviation(index: int, diff: float) -> RuleIssue:
    issue = {"code": "PITCH_DEVIATION", "wordIndex": index, "data": {"meanDiffSt": diff}}
    return RuleIssue(issue, abs(diff))


def _flat(pitch_range: float = 0.3) -> RuleIssue:
    issue = {"code": "FLAT_PITCH", "data": {"pitchRange": pitch_range}}
    return RuleIssue(issue, 1.0 - pitch_range)


def test_stress_mismatch_template() -> None:
    issue = _stress("expect", "honestly").issue

    assert render_tip(issue, WORDS) == "Nhấn vào *expect*, không phải *honestly*."


def test_extra_pause_template_names_the_word_at_wordindex_and_rounds_the_milliseconds() -> None:
    assert render_tip(_pause(2, 520.0).issue, WORDS) == "Đọc liền qua *bravo*, đừng ngắt (520 ms)."
    assert render_tip(_pause(2, 519.6).issue, WORDS) == "Đọc liền qua *bravo*, đừng ngắt (520 ms)."


def test_final_contour_template_follows_the_original_direction_and_names_the_last_word() -> None:
    falling = _final(-10.8, 9.7).issue
    rising = _final(10.8, -9.7).issue

    assert render_tip(falling, WORDS) == "Xuống giọng ở cuối câu, ở *out*; bạn đang lên giọng."
    assert render_tip(rising, WORDS) == "Lên giọng ở cuối câu, ở *out*; bạn đang xuống giọng."


def test_pitch_deviation_template_follows_the_sign_of_the_difference() -> None:
    higher = _deviation(1, 3.4).issue
    lower = _deviation(1, -3.4).issue

    assert render_tip(higher, WORDS) == "Bạn đang đọc cao hơn bản gốc ở *Brown*; hạ giọng xuống."
    assert render_tip(lower, WORDS) == "Bạn đang đọc thấp hơn bản gốc ở *Brown*; nâng giọng lên."


def test_flat_pitch_template() -> None:
    assert render_tip(_flat().issue, WORDS) == "Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc."


def test_asterisks_in_a_word_never_reach_the_marker_syntax() -> None:
    words = ["a*b", "**x**", " spaced ", "ok", "end*"]

    assert render_tip(_deviation(0, 4.0).issue, words) == (
        "Bạn đang đọc cao hơn bản gốc ở *ab*; hạ giọng xuống."
    )
    assert render_tip(_pause(2, 300.0).issue, words) == "Đọc liền qua *spaced*, đừng ngắt (300 ms)."
    assert render_tip(_stress("a*b", "**x**").issue, words) == ("Nhấn vào *ab*, không phải *x*.")
    assert render_tip(_final(-9.0, 9.0).issue, words) == (
        "Xuống giọng ở cuối câu, ở *end*; bạn đang lên giọng."
    )


@pytest.mark.parametrize(
    "issue",
    [
        _deviation(9, 4.0).issue,  # wordIndex ngoài danh sách từ
        _pause(0, 300.0).issue,  # từ chỉ có dấu sao: không còn gì để gạch chân
        _stress("***", "x").issue,
        {"code": "PHONE", "wordIndex": 0, "data": {}},  # mã chưa có template ở Phase 3
    ],
)
def test_an_issue_without_a_safe_wording_renders_nothing(issue: dict[str, Any]) -> None:
    assert render_tip(issue, ["***", "b", "c"]) is None


def test_five_codes_give_three_tips_in_priority_order() -> None:
    issues = [
        _flat(),
        _deviation(1, 3.4),
        _pause(2, 520.0),
        _final(-10.8, 9.7),
        _stress("Brown", "fox", index=1),
    ]

    tips = select_tips(issues, WORDS)

    assert [issues[t["issueRef"]].issue["code"] for t in tips] == [
        "STRESS_MISMATCH",
        "FINAL_CONTOUR",
        "EXTRA_PAUSE",
    ]
    assert [t["issueRef"] for t in tips] == [4, 3, 2]
    assert all(t["source"] == "template" for t in tips)
    assert len(issues) == 5, "issues giữ nguyên đủ mọi issue"


def test_the_most_deviant_issue_wins_inside_a_code() -> None:
    issues = [_deviation(0, 3.2), _deviation(3, 4.1)]

    tips = select_tips(issues, WORDS)

    assert tips == [
        {
            "text": "Bạn đang đọc cao hơn bản gốc ở *fox*; hạ giọng xuống.",
            "issueRef": 1,
            "source": "template",
        }
    ]


def test_each_code_picks_its_own_severity_measure() -> None:
    pauses = [_pause(0, 300.0), _pause(2, 640.0), _pause(3, 410.0)]

    assert select_tips(pauses, WORDS)[0]["issueRef"] == 1
    assert (
        select_tips([_stress("a", "b", severity=0.9), _stress("c", "d", severity=1.7)], WORDS)[0][
            "issueRef"
        ]
        == 1
    )


def test_a_tie_in_severity_keeps_the_earlier_issue() -> None:
    assert select_tips([_deviation(0, 3.5), _deviation(1, -3.5)], WORDS)[0]["issueRef"] == 0


def test_no_issue_gives_no_tip() -> None:
    assert select_tips([], WORDS) == []


def test_an_unrenderable_issue_falls_back_to_the_next_best_one_of_the_same_code() -> None:
    issues = [
        _deviation(1, 3.2),
        _deviation(9, 9.0),
    ]  # issue lệch nhiều nhất trỏ ra ngoài danh sách

    assert [t["issueRef"] for t in select_tips(issues, WORDS)] == [0]


def test_every_tip_points_at_an_issue_of_the_same_code() -> None:
    issues = [_stress("a", "b"), _final(-9.0, 9.0), _pause(1, 400.0), _deviation(2, 3.5), _flat()]
    templates = {
        "STRESS_MISMATCH": "Nhấn vào",
        "FINAL_CONTOUR": "giọng ở cuối câu",
        "EXTRA_PAUSE": "Đọc liền qua",
        "PITCH_DEVIATION": "Bạn đang đọc",
        "FLAT_PITCH": "Giọng hơi phẳng",
    }

    tips = select_tips(issues, WORDS)

    assert 1 <= len(tips) <= 3
    assert len({issues[t["issueRef"]].issue["code"] for t in tips}) == len(tips)
    for tip in tips:
        code = issues[tip["issueRef"]].issue["code"]
        assert code in PRIORITY
        assert templates[code] in tip["text"]
        assert tip["source"] == "template"


def test_a_scored_pause_yields_a_validated_tip_that_names_the_right_word() -> None:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    user, _ = synth_sentence(DEFAULT_WORDS, extra_gap_after={0: 0.5}, seed=1)
    words = [RefWord(t, s, e) for t, s, e in marks]

    score = score_prosody(prepare_features(audio), prepare_features(user), words)
    result = to_score_result(
        score, lesson_id="01TESTLESSON", segment_index=0, attempt=1, timing_ms={"rules": 1.0}
    )

    assert isinstance(result, ScoreResult)
    assert [i.root.code for i in result.issues] == ["EXTRA_PAUSE"]
    assert [(t.issue_ref, t.source) for t in result.tips] == [(0, "template")]
    assert result.tips[0].text.startswith("Đọc liền qua *alpha*, đừng ngắt (")

"""Tip template tiếng Việt và chọn tip theo D-14 (03-06, RUL-02)."""

from __future__ import annotations

import math
import re
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


FLAT_30 = (
    "Độ lên xuống của bạn chỉ bằng khoảng 30% bản gốc; "
    "mở rộng giọng, lên cao và xuống thấp rõ hơn.",
    "Giọng còn phẳng (khoảng 30% độ lên xuống của bản gốc). "
    "Nghe lại bản gốc và bắt chước chỗ giọng vút lên, hạ xuống.",
    "Thử phóng đại ngữ điệu một chút: bạn mới lên xuống được khoảng 30% so với bản gốc.",
    'Bản gốc lên xuống nhiều hơn bạn (bạn ≈ 30%); đừng ngại đọc hơi "quá", thường sẽ vừa.',
)


@pytest.mark.parametrize("variant", range(4))
def test_flat_pitch_has_four_approved_variants_with_the_measured_percentage(variant: int) -> None:
    assert render_tip(_flat(0.3).issue, WORDS, variant=variant) == FLAT_30[variant]


def test_flat_pitch_variant_wraps_around() -> None:
    assert render_tip(_flat(0.3).issue, WORDS, variant=4) == FLAT_30[0]
    assert render_tip(_flat(0.3).issue, WORDS, variant=9) == FLAT_30[1]


@pytest.mark.parametrize(
    ("pitch_range", "pct"),
    [(0.33, 35), (0.125, 15), (0.0015, 0), (0.64, 65), (0.3, 30), (0.375, 40)],
)
def test_flat_pitch_percentage_is_rounded_half_up_to_a_multiple_of_five(
    pitch_range: float, pct: int
) -> None:
    text = render_tip(_flat(pitch_range).issue, WORDS)

    assert text is not None
    assert f"{pct}%" in text


@pytest.mark.parametrize(
    "pitch_range", [float("nan"), float("inf"), float("-inf"), "0.3", True, None]
)
def test_flat_pitch_without_a_finite_number_renders_nothing(pitch_range: object) -> None:
    issue = {"code": "FLAT_PITCH", "data": {"pitchRange": pitch_range}}

    assert render_tip(issue, WORDS) is None
    assert render_tip({"code": "FLAT_PITCH", "data": {}}, WORDS) is None


def test_the_variant_follows_segment_and_attempt_and_is_deterministic() -> None:
    issues = [_flat(0.3)]

    def text(segment_index: int, attempt: int) -> str:
        return select_tips(issues, WORDS, segment_index=segment_index, attempt=attempt)[0]["text"]

    assert text(0, 1) == FLAT_30[0]
    assert text(0, 2) == FLAT_30[1]
    assert text(1, 1) == text(0, 2)
    assert text(0, 5) == text(0, 1)
    assert text(2, 3) == text(2, 3)
    assert len({text(0, attempt) for attempt in range(1, 5)}) == 4


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

    tips = select_tips(issues, WORDS, segment_index=0, attempt=1)

    assert [issues[t["issueRef"]].issue["code"] for t in tips] == [
        "STRESS_MISMATCH",
        "FINAL_CONTOUR",
        "EXTRA_PAUSE",
    ]
    assert [t["issueRef"] for t in tips] == [4, 3, 2]
    assert all(t["source"] == "template" for t in tips)
    assert len(issues) == 5, "issues giữ nguyên đủ mọi issue"


def test_the_most_deviant_issue_of_a_code_gets_the_first_tip() -> None:
    issues = [_deviation(0, 3.2), _deviation(3, 4.1)]

    tips = select_tips(issues, WORDS, segment_index=0, attempt=1)

    assert [t["issueRef"] for t in tips] == [1, 0]
    assert tips[0] == {
        "text": "Bạn đang đọc cao hơn bản gốc ở *fox*; hạ giọng xuống.",
        "issueRef": 1,
        "source": "template",
    }


def test_each_code_picks_its_own_severity_measure() -> None:
    pauses = [_pause(0, 300.0), _pause(2, 640.0), _pause(3, 410.0)]

    assert select_tips(pauses, WORDS, segment_index=0, attempt=1)[0]["issueRef"] == 1
    assert (
        select_tips(
            [_stress("a", "b", severity=0.9), _stress("c", "d", severity=1.7)],
            WORDS,
            segment_index=0,
            attempt=1,
        )[0]["issueRef"]
        == 1
    )


def test_a_tie_in_severity_keeps_the_earlier_issue() -> None:
    assert (
        select_tips([_deviation(0, 3.5), _deviation(1, -3.5)], WORDS, segment_index=0, attempt=1)[
            0
        ]["issueRef"]
        == 0
    )


def test_no_issue_gives_no_tip() -> None:
    assert select_tips([], WORDS, segment_index=0, attempt=1) == []


def test_an_unrenderable_issue_falls_back_to_the_next_best_one_of_the_same_code() -> None:
    issues = [
        _deviation(1, 3.2),
        _deviation(9, 9.0),
    ]  # issue lệch nhiều nhất trỏ ra ngoài danh sách

    assert [t["issueRef"] for t in select_tips(issues, WORDS, segment_index=0, attempt=1)] == [0]


def test_every_tip_points_at_an_issue_of_the_same_code() -> None:
    issues = [_stress("a", "b"), _final(-9.0, 9.0), _pause(1, 400.0), _deviation(2, 3.5), _flat()]
    templates = {
        "STRESS_MISMATCH": "Nhấn vào",
        "FINAL_CONTOUR": "giọng ở cuối câu",
        "EXTRA_PAUSE": "Đọc liền qua",
        "PITCH_DEVIATION": "Bạn đang đọc",
        "FLAT_PITCH": "Độ lên xuống của bạn",
    }

    tips = select_tips(issues, WORDS, segment_index=0, attempt=1)

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


def _flat_learner_score() -> Any:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    words = [RefWord(t, s, e) for t, s, e in marks]
    return score_prosody(prepare_features(audio), prepare_features(flat), words)


def test_a_scored_flat_learner_gets_four_different_flat_sentences_with_its_own_percentage() -> None:
    score = _flat_learner_score()
    assert [i["code"] for i in score.issues] == ["FLAT_PITCH"]
    pct = int(math.floor(score.issues[0]["data"]["pitchRange"] * 20 + 0.5) * 5)

    texts = []
    for attempt in range(1, 5):
        result = to_score_result(
            score,
            lesson_id="01TESTLESSON",
            segment_index=0,
            attempt=attempt,
            timing_ms={"rules": 1.0},
        )
        assert [(t.issue_ref, t.source) for t in result.tips] == [(0, "template")]
        assert f"{pct}%" in result.tips[0].text
        texts.append(result.tips[0].text)

    assert len(set(texts)) == 4


def test_self_compare_still_yields_no_tip() -> None:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    features = prepare_features(audio)
    words = [RefWord(t, s, e) for t, s, e in marks]

    result = to_score_result(
        score_prosody(features, features, words),
        lesson_id="01TESTLESSON",
        segment_index=0,
        attempt=1,
        timing_ms={"rules": 1.0},
    )

    assert result.tips == []


# --- Task 2: đủ biến thể cho mọi mã, chọn tip hai lượt (D-14 sửa, D-16) -----------------------

_MARK = re.compile(r"\*([^*]+)\*")

# Lời văn đã duyệt (03-GAP-TIPS-PROPOSAL.md mục A), chép lại độc lập với tips.py.
# Mỗi dòng: (tên, issue, các cách nói đã điền số).
_VARIANTS: list[tuple[str, dict[str, Any], tuple[str, ...]]] = [
    (
        "EXTRA_PAUSE",
        _pause(2, 519.6).issue,
        (
            "Đọc liền qua *bravo*, đừng ngắt (520 ms).",
            "Bạn dừng 520 ms sau *bravo*, bản gốc đọc nối luôn; nối *bravo* với từ sau.",
            "Bỏ khoảng nghỉ sau *bravo* (520 ms): giữ hơi và đọc trọn cụm.",
        ),
    ),
    (
        "FINAL_CONTOUR falling",
        _final(-10.8, 9.7).issue,
        (
            "Xuống giọng ở cuối câu, ở *out*; bạn đang lên giọng.",
            "Cuối câu bản gốc hạ giọng ở *out*, còn bạn lại lên nên nghe như đang hỏi. "
            "Kết thúc dứt khoát, hạ xuống.",
            "Ở *out*, để giọng rơi xuống như kết thúc một ý, đừng kéo lên.",
        ),
    ),
    (
        "FINAL_CONTOUR rising",
        _final(10.8, -9.7).issue,
        (
            "Lên giọng ở cuối câu, ở *out*; bạn đang xuống giọng.",
            "Bản gốc kéo giọng lên ở *out* (giọng hỏi hoặc chưa nói hết ý), bạn lại hạ xuống; "
            "kết thúc bằng giọng đi lên.",
            "Ở *out*, nâng giọng lên ở cuối như bản gốc thay vì hạ xuống.",
        ),
    ),
    (
        "PITCH_DEVIATION higher",
        _deviation(1, 3.4).issue,
        (
            "Bạn đang đọc cao hơn bản gốc ở *Brown*; hạ giọng xuống.",
            "*Brown* của bạn cao hơn bản gốc khoảng 3.5 nửa cung; đọc từ này thấp và nhẹ hơn.",
            "Hạ *Brown* xuống chừng 3.5 nửa cung cho khớp bản gốc.",
        ),
    ),
    (
        "PITCH_DEVIATION lower",
        _deviation(1, -3.4).issue,
        (
            "Bạn đang đọc thấp hơn bản gốc ở *Brown*; nâng giọng lên.",
            "*Brown* của bạn thấp hơn bản gốc khoảng 3.5 nửa cung; đẩy giọng lên ở từ này.",
            "Nâng *Brown* lên chừng 3.5 nửa cung, bản gốc nói từ này cao hơn.",
        ),
    ),
    (
        "STRESS_MISMATCH",
        _stress("expect", "honestly").issue,
        (
            "Nhấn vào *expect*, không phải *honestly*.",
            "Bản gốc nhấn mạnh nhất ở *expect*, bạn lại nhấn *honestly*. "
            "Đọc *expect* to, dài và cao hơn một chút.",
            "Dồn trọng âm của câu về *expect*; *honestly* nên đọc nhẹ đi.",
        ),
    ),
]


@pytest.mark.parametrize(
    ("issue", "expected"), [(i, e) for _, i, e in _VARIANTS], ids=[n for n, _, _ in _VARIANTS]
)
def test_every_code_renders_each_approved_variant_and_wraps_around(
    issue: dict[str, Any], expected: tuple[str, ...]
) -> None:
    n = len(expected)

    for variant in range(n):
        assert render_tip(issue, WORDS, variant=variant) == expected[variant]
        assert render_tip(issue, WORDS, variant=variant + n) == expected[variant]
    assert len({render_tip(issue, WORDS, variant=v) for v in range(n)}) == n


def test_the_default_variant_is_the_first_one() -> None:
    assert render_tip(_pause(2, 520.0).issue, WORDS) == "Đọc liền qua *bravo*, đừng ngắt (520 ms)."


@pytest.mark.parametrize(("user_ms", "shown"), [(519.6, "520"), (520.5, "521"), (300.0, "300")])
def test_extra_pause_milliseconds_are_rounded_half_up(user_ms: float, shown: str) -> None:
    text = render_tip(_pause(2, user_ms).issue, WORDS, variant=1)

    assert text is not None
    assert text.startswith(f"Bạn dừng {shown} ms sau ")


@pytest.mark.parametrize(
    ("diff", "shown"),
    [(3.4, "3.5"), (3.2, "3"), (3.25, "3.5"), (-4.1, "4"), (3.75, "4"), (4.0, "4"), (-3.6, "3.5")],
)
def test_half_steps_are_rounded_to_half_a_semitone_and_never_print_a_trailing_zero(
    diff: float, shown: str
) -> None:
    text = render_tip(_deviation(1, diff).issue, WORDS, variant=2)

    assert text is not None
    assert f"chừng {shown} nửa cung" in text
    assert ".0" not in text


@pytest.mark.parametrize(
    "issue",
    [
        {"code": "EXTRA_PAUSE", "wordIndex": 2, "data": {"userMs": float("nan")}},
        {"code": "EXTRA_PAUSE", "wordIndex": 2, "data": {"userMs": float("inf")}},
        {"code": "PITCH_DEVIATION", "wordIndex": 1, "data": {"meanDiffSt": float("nan")}},
        {"code": "PITCH_DEVIATION", "wordIndex": 1, "data": {"meanDiffSt": float("-inf")}},
        {"code": "PITCH_DEVIATION", "wordIndex": 1, "data": {"meanDiffSt": 0.0}},
        {"code": "FINAL_CONTOUR", "data": {"refSlope": -1.0, "userSlope": -2.0}},
        {"code": "FINAL_CONTOUR", "data": {"refSlope": float("nan"), "userSlope": 1.0}},
    ],
)
def test_a_non_finite_or_contradictory_number_renders_nothing_for_every_variant(
    issue: dict[str, Any],
) -> None:
    for variant in range(4):
        assert render_tip(issue, WORDS, variant=variant) is None


def _marked(text: str) -> list[str]:
    return _MARK.findall(text)


_HOSTILE = ["a*b", "**x**", "{pct}", "<b>x</b>"]


@pytest.mark.parametrize("variant", range(5))
def test_untrusted_words_never_open_or_close_a_marker_in_any_variant(variant: int) -> None:
    cases = [
        (_pause(0, 300.0).issue, {"ab"}),
        (_pause(1, 300.0).issue, {"x"}),
        (_pause(2, 300.0).issue, {"{pct}"}),
        (_deviation(0, 4.0).issue, {"ab"}),
        (_deviation(3, -4.0).issue, {"<b>x</b>"}),
        (_final(-9.0, 9.0).issue, {"<b>x</b>"}),
        (_final(9.0, -9.0).issue, {"<b>x</b>"}),
    ]

    for issue, markers in cases:
        text = render_tip(issue, _HOSTILE, variant=variant)
        assert text is not None
        assert set(_marked(text)) == markers
        assert text.count("*") == 2 * len(_marked(text))

    stress = render_tip(_stress("a*b", "**x**").issue, _HOSTILE, variant=variant)
    assert stress is not None
    assert set(_marked(stress)) == {"ab", "x"}
    assert stress.count("*") == 2 * len(_marked(stress))


@pytest.mark.parametrize("variant", range(4))
def test_a_word_made_only_of_asterisks_renders_nothing_in_any_variant(variant: int) -> None:
    words = ["***", "b", "**"]

    assert render_tip(_pause(0, 300.0).issue, words, variant=variant) is None
    assert render_tip(_deviation(0, 4.0).issue, words, variant=variant) is None
    assert render_tip(_final(-9.0, 9.0).issue, words, variant=variant) is None
    assert render_tip(_stress("***", "x").issue, words, variant=variant) is None
    assert render_tip(_stress("x", "**").issue, words, variant=variant) is None


@pytest.mark.parametrize("variant", range(3))
def test_in_a_stress_tip_only_the_second_marker_is_the_learners_word(variant: int) -> None:
    text = render_tip(_stress("expect", "honestly").issue, WORDS, variant=variant)

    assert text is not None
    markers = _marked(text)
    assert markers[1] == "honestly"
    assert all(m == "expect" for i, m in enumerate(markers) if i != 1)
    assert len(markers) == (3 if variant == 1 else 2)


def _tips(issues: list[RuleIssue], *, segment_index: int = 0, attempt: int = 1) -> list[Any]:
    return select_tips(issues, WORDS, segment_index=segment_index, attempt=attempt)


def _codes(issues: list[RuleIssue], tips: list[Any]) -> list[str]:
    return [issues[t["issueRef"]].issue["code"] for t in tips]


def test_a_second_word_level_issue_of_one_code_earns_a_second_tip_with_the_next_wording() -> None:
    issues = [_deviation(0, 4.1), _deviation(3, 3.2)]

    tips = _tips(issues)

    assert [t["issueRef"] for t in tips] == [0, 1]
    assert tips[0]["text"] == "Bạn đang đọc cao hơn bản gốc ở *The*; hạ giọng xuống."
    assert tips[1]["text"] == (
        "*fox* của bạn cao hơn bản gốc khoảng 3 nửa cung; đọc từ này thấp và nhẹ hơn."
    )
    assert all(t["source"] == "template" for t in tips)


def test_the_second_tip_moves_with_the_attempt_too() -> None:
    issues = [_deviation(0, 4.1), _deviation(3, 3.2)]

    tips = _tips(issues, attempt=2)

    assert tips[0]["text"].startswith("*The* của bạn cao hơn")
    assert tips[1]["text"].startswith("Hạ *fox* xuống chừng 3 nửa cung")


def test_no_code_gets_more_than_two_tips() -> None:
    issues = [_deviation(0, 4.1), _deviation(2, 3.9), _deviation(3, 3.2)]

    assert [t["issueRef"] for t in _tips(issues)] == [0, 1]


def test_pass_two_adds_extra_pause_before_pitch_deviation_and_stops_at_three() -> None:
    issues = [
        _pause(0, 600.0),
        _pause(1, 500.0),
        _pause(2, 400.0),
        _deviation(3, 5.0),
        _deviation(4, 4.0),
        _deviation(1, 3.5),
    ]

    tips = _tips(issues)

    assert [t["issueRef"] for t in tips] == [0, 1, 3]
    assert _codes(issues, tips) == ["EXTRA_PAUSE", "EXTRA_PAUSE", "PITCH_DEVIATION"]


def test_pass_two_never_names_a_word_twice() -> None:
    issues = [_pause(2, 500.0), _deviation(0, 4.0), _deviation(2, 3.5)]

    assert [t["issueRef"] for t in _tips(issues)] == [0, 1]


def test_pass_two_falls_back_to_the_next_word_that_is_still_free() -> None:
    issues = [_pause(2, 500.0), _deviation(0, 4.0), _deviation(2, 3.5), _deviation(3, 3.3)]

    assert [t["issueRef"] for t in _tips(issues)] == [0, 1, 3]


def test_a_final_contour_tip_blocks_a_second_pitch_tip_on_the_last_word() -> None:
    issues = [_final(-9.0, 9.0), _deviation(0, 4.0), _deviation(4, 3.5)]

    assert [t["issueRef"] for t in _tips(issues)] == [0, 1]


def test_the_stress_words_index_blocks_a_second_tip_on_that_word() -> None:
    issues = [_stress("Brown", "fox", index=1), _deviation(0, 4.0), _deviation(1, 3.5)]

    assert [t["issueRef"] for t in _tips(issues)] == [0, 1]


@pytest.mark.parametrize(
    "issues",
    [
        [_stress("a", "b"), _stress("c", "d", index=3)],
        [_final(-9.0, 9.0), _final(-8.0, 8.0)],
        [_flat(0.3), _flat(0.2)],
    ],
)
def test_sentence_level_codes_never_get_a_second_tip(issues: list[RuleIssue]) -> None:
    assert len(_tips(issues)) == 1


def test_pass_two_never_displaces_a_pass_one_tip() -> None:
    issues = [
        _flat(),
        _deviation(1, 3.4),
        _deviation(3, 3.1),
        _pause(2, 520.0),
        _pause(0, 300.0),
        _final(-10.8, 9.7),
        _stress("Brown", "fox", index=1),
    ]

    tips = _tips(issues)

    assert _codes(issues, tips) == ["STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE"]
    assert [t["issueRef"] for t in tips] == [6, 5, 3]


def test_output_is_ordered_by_priority_then_by_rank_inside_a_code() -> None:
    issues = [_flat(), _deviation(3, 3.2), _deviation(0, 4.1)]

    tips = _tips(issues)

    assert _codes(issues, tips) == ["PITCH_DEVIATION", "PITCH_DEVIATION", "FLAT_PITCH"]
    assert [t["issueRef"] for t in tips] == [2, 1, 0]


def test_a_single_issue_still_gives_a_single_tip() -> None:
    assert len(_tips([_pause(2, 520.0)])) == 1
    assert len(_tips([_deviation(2, 4.0)])) == 1


def test_the_same_attempt_always_renders_the_same_text() -> None:
    issues = [_pause(0, 600.0), _pause(1, 500.0), _deviation(3, 5.0), _flat()]

    assert _tips(issues, segment_index=2, attempt=3) == _tips(issues, segment_index=2, attempt=3)


def test_every_tip_names_the_word_of_the_issue_it_points_at() -> None:
    issues = [
        _flat(),
        _deviation(3, 3.2),
        _deviation(0, 4.1),
        _pause(2, 500.0),
        _pause(4, 450.0),
        _final(-10.8, 9.7),
        _stress("Brown", "fox", index=1),
    ]

    for segment_index in range(2):
        for attempt in range(1, 5):
            for subset in (issues, issues[:5], issues[1:4], issues[3:]):
                tips = _tips(subset, segment_index=segment_index, attempt=attempt)
                assert 1 <= len(tips) <= 3
                for tip in tips:
                    issue = subset[tip["issueRef"]].issue
                    marked = _marked(tip["text"])
                    if issue["code"] in ("EXTRA_PAUSE", "PITCH_DEVIATION"):
                        assert set(marked) == {WORDS[issue["wordIndex"]]}
                    elif issue["code"] == "FINAL_CONTOUR":
                        assert set(marked) == {WORDS[-1]}
                    elif issue["code"] == "STRESS_MISMATCH":
                        assert marked[0] == issue["data"]["refWord"]
                        assert marked[1] == issue["data"]["userWord"]
                    else:
                        assert marked == []

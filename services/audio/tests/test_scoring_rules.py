"""Rule engine Lớp C trên tín hiệu tổng hợp (03-06, RUL-01, D-12).

Không có audio thật trong repo: mọi tín hiệu từ `synth.py`. Các cổng chắc chắn được thử trực tiếp
trên `RuleInput` dựng tay để không phụ thuộc vào chi tiết của F0/DTW.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import numpy as np
import pytest
from synth import DEFAULT_WORDS, SynthWord, synth_sentence

from audio_service.contracts_gen import ScoreResult
from audio_service.rules.engine import (
    RuleInput,
    extra_pause,
    final_contour,
    flat_pitch,
    pitch_deviation,
    run_rules,
    stress_mismatch,
)
from audio_service.scoring.align import Alignment, linear_path
from audio_service.scoring.features import ProsodyFeatures, prepare_features
from audio_service.scoring.scorer import ProsodyScore, RefWord, score_prosody, to_score_result

Marks = list[tuple[str, float, float]]


@pytest.fixture(scope="module")
def reference() -> tuple[np.ndarray, Marks, ProsodyFeatures]:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    return audio, marks, prepare_features(audio)


def _words(marks: Marks) -> list[RefWord]:
    return [RefWord(text=t, start_s=s, end_s=e) for t, s, e in marks]


def _score(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures], user_audio: np.ndarray
) -> ProsodyScore:
    _, marks, ref_feats = reference
    return score_prosody(ref_feats, prepare_features(user_audio), _words(marks))


def _features(st: np.ndarray) -> ProsodyFeatures:
    n = int(st.shape[0])
    return ProsodyFeatures(
        f0_st=st,
        voiced=np.isfinite(st),
        energy_db=np.full(n, -20.0),
        mfcc=np.zeros((n, 12)),
        trim_start=0,
        trim_end=n,
    )


def _rule_input(ref_st: np.ndarray, user_st: np.ndarray, pitch_range: float) -> RuleInput:
    """RuleInput dựng tay: hai contour cùng độ dài, căn đường chéo, một "từ" phủ cả câu."""
    n = int(ref_st.shape[0])
    return RuleInput(
        ref=_features(ref_st),
        user=_features(user_st),
        alignment=Alignment(path=linear_path(n, n), cost=0.0, ratio=1.0, ok=True, linear=False),
        words=["whole"],
        ref_word_frames=[(0, n)],
        user_word_frames=[(0, n)],
        user_st_on_ref=user_st,
        pitch_range=pitch_range,
        ref_prominence=np.zeros(1),
        user_prominence=np.zeros(1),
        word_issues_allowed=True,
    )


def test_self_compare_has_stress_entries_and_no_issue_or_tip(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    audio, marks, ref_feats = reference
    score = score_prosody(ref_feats, ref_feats, _words(marks))

    assert [e["word"] for e in score.stress] == [w.text for w in DEFAULT_WORDS]
    for entry in score.stress:
        assert math.isfinite(entry["ref"]) and math.isfinite(entry["user"])
        assert entry["ref"] == pytest.approx(entry["user"], abs=1e-9)
    assert score.pauses == []
    assert score.issues == []
    assert score.tips == []


def test_flat_learner_yields_one_flat_pitch_issue_and_one_template_tip(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    score = _score(reference, flat)

    assert [i["code"] for i in score.issues] == ["FLAT_PITCH"]
    assert score.issues[0]["data"]["pitchRange"] < 0.6
    assert score.tips == [
        {
            "text": "Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc.",
            "issueRef": 0,
            "source": "template",
        }
    ]


def test_flat_learner_result_validates_as_score_result(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    score = _score(reference, flat)
    result = to_score_result(
        score, lesson_id="01TESTLESSON", segment_index=0, attempt=1, timing_ms={"rules": 1.0}
    )

    assert isinstance(result, ScoreResult)
    assert [i.root.code for i in result.issues] == ["FLAT_PITCH"]
    assert [(t.issue_ref, t.source) for t in result.tips] == [(0, "template")]


def test_flat_pitch_is_skipped_when_the_original_is_flat_too() -> None:
    t = np.linspace(0.0, 4.0 * np.pi, 120)
    ref_st = 0.5 * np.sin(t)  # std ~0.35 st: bản gốc gần phẳng (< FLAT_REF_MIN_STD_ST)
    user_st = 0.05 * np.sin(t)  # người học còn phẳng hơn, pitchRange = 0.1

    assert flat_pitch(_rule_input(ref_st, user_st, pitch_range=0.1)) is None
    assert run_rules(_rule_input(ref_st, user_st, pitch_range=0.1)) == []


def test_flat_pitch_fires_when_original_moves_and_learner_is_flat() -> None:
    t = np.linspace(0.0, 4.0 * np.pi, 120)
    ref_st = 4.0 * np.sin(t)
    user_st = 0.4 * np.sin(t)

    issue = flat_pitch(_rule_input(ref_st, user_st, pitch_range=0.1))

    assert issue is not None
    assert issue.issue == {"code": "FLAT_PITCH", "data": {"pitchRange": 0.1}}
    assert issue.severity == pytest.approx(0.9)


def test_flat_pitch_stays_silent_when_pitch_range_is_not_low() -> None:
    t = np.linspace(0.0, 4.0 * np.pi, 120)

    assert flat_pitch(_rule_input(4.0 * np.sin(t), 3.5 * np.sin(t), pitch_range=0.9)) is None


def test_flat_pitch_stays_silent_when_learner_is_not_flatter_than_the_original() -> None:
    t = np.linspace(0.0, 4.0 * np.pi, 120)

    # pitchRange thấp vì người học dao động QUÁ nhiều, không phải phẳng.
    assert flat_pitch(_rule_input(2.5 * np.sin(t), 9.0 * np.sin(t), pitch_range=0.28)) is None


# --- Task 2: bốn rule còn lại với cổng chắc chắn (D-12, D-13) và giới hạn khi căn kém (D-02) ---
# Phần 1: RuleInput dựng tay, để thử từng cổng mà không phụ thuộc chi tiết F0/DTW.

_N = 220  # khung của bản gốc
_FRAMES = [(10, 50), (53, 93), (96, 136), (139, 179), (182, 196)]  # 5 từ, khe 3 khung
_WORDS = ["alpha", "bravo", "charlie", "delta", "echo"]
_GATE_STRESS = np.array([0.0, 2.0, 0.5, 0.0, -1.0])


def _db(n: int = _N, silent: list[tuple[int, int]] | None = None) -> np.ndarray:
    """Năng lượng dB: 0 dB trong từ và đoạn nền sau câu (200-215), -80 dB ở các khe và hai đầu."""
    db = np.full(n, -80.0)
    for start, end in _FRAMES:
        db[start:end] = 0.0
    db[200:215] = 0.0
    for start, end in silent or []:
        db[start:end] = -80.0
    return db


def _feats(st: np.ndarray, db: np.ndarray) -> ProsodyFeatures:
    n = int(st.shape[0])
    return ProsodyFeatures(
        f0_st=st,
        voiced=np.isfinite(st),
        energy_db=db,
        mfcc=np.zeros((n, 12)),
        trim_start=0,
        trim_end=n,
    )


def _crafted(
    *,
    ref_st: np.ndarray | None = None,
    user_st: np.ndarray | None = None,
    ref_db: np.ndarray | None = None,
    user_db: np.ndarray | None = None,
    path: np.ndarray | None = None,
    ref_prom: np.ndarray | None = None,
    user_prom: np.ndarray | None = None,
    pitch_range: float = 1.0,
    allowed: bool = True,
) -> RuleInput:
    ref_st = np.zeros(_N) if ref_st is None else ref_st
    user_st = ref_st.copy() if user_st is None else user_st
    ref_db = _db() if ref_db is None else ref_db
    user_db = ref_db if user_db is None else user_db
    path = linear_path(_N, _N) if path is None else path
    n_user = int(user_st.shape[0])
    st_on_ref = user_st[path[:, 1]] if path.shape[0] == _N else np.full(_N, np.nan)
    return RuleInput(
        ref=_feats(ref_st, ref_db),
        user=_feats(user_st, user_db),
        alignment=Alignment(
            path=path,
            cost=0.0 if allowed else float("inf"),
            ratio=n_user / _N,
            ok=allowed,
            linear=not allowed,
        ),
        words=list(_WORDS),
        ref_word_frames=list(_FRAMES),
        user_word_frames=list(_FRAMES),
        user_st_on_ref=st_on_ref,
        pitch_range=pitch_range,
        ref_prominence=_GATE_STRESS.copy() if ref_prom is None else ref_prom,
        user_prominence=_GATE_STRESS.copy() if user_prom is None else user_prom,
        word_issues_allowed=allowed,
    )


def _wave() -> np.ndarray:
    return 2.0 * np.sin(np.arange(_N) / 10.0)


def _tail_contour(slope_st_s: float, *, finite: int = 30) -> np.ndarray:
    """Contour 0 st rồi 30 khung cuối có độ dốc cho trước; chỉ `finite` khung cuối là hữu hạn."""
    st = np.zeros(_N)
    st[-30:] = slope_st_s * np.arange(30) * 0.01
    if finite < 30:
        st[-30:-finite] = np.nan
    return st


# FINAL_CONTOUR -----------------------------------------------------------------------------


def test_final_contour_fires_on_opposite_slopes_inside_the_gate() -> None:
    inp = _crafted(ref_st=_tail_contour(-10.0), user_st=_tail_contour(10.0))

    found = final_contour(inp)

    assert found is not None
    assert found.issue["code"] == "FINAL_CONTOUR"
    assert found.issue["data"]["refSlope"] == pytest.approx(-10.0, abs=0.1)
    assert found.issue["data"]["userSlope"] == pytest.approx(10.0, abs=0.1)
    assert found.severity == pytest.approx(20.0, abs=0.2)


@pytest.mark.parametrize(
    ("ref_slope", "user_slope"),
    [
        (-10.0, -8.0),  # cùng chiều
        (10.0, 12.0),
        (-10.0, 40.0),  # |slope| người học > FINAL_SLOPE_MAX_ST_S (nghi lỗi quãng tám)
        (-45.0, 10.0),  # |slope| bản gốc > FINAL_SLOPE_MAX_ST_S
        (-4.0, 10.0),  # |slope| bản gốc < FINAL_SLOPE_MIN_ST_S
        (-10.0, 3.0),  # |slope| người học < FINAL_SLOPE_MIN_ST_S
    ],
)
def test_final_contour_stays_silent_outside_the_slope_gate(
    ref_slope: float, user_slope: float
) -> None:
    inp = _crafted(ref_st=_tail_contour(ref_slope), user_st=_tail_contour(user_slope))

    assert final_contour(inp) is None


def test_final_contour_needs_enough_voiced_frames_on_both_sides() -> None:
    enough = _crafted(ref_st=_tail_contour(-10.0), user_st=_tail_contour(10.0, finite=15))
    too_few = _crafted(ref_st=_tail_contour(-10.0), user_st=_tail_contour(10.0, finite=14))
    ref_few = _crafted(ref_st=_tail_contour(-10.0, finite=14), user_st=_tail_contour(10.0))

    assert final_contour(enough) is not None
    assert final_contour(too_few) is None
    assert final_contour(ref_few) is None


def test_final_contour_reads_the_aligned_user_tail_when_the_alignment_is_ok() -> None:
    """03-11: mép cắt lệch vài khung làm đuôi riêng của người học rơi vào đoạn khác. Khi căn ok,
    rule so 300 ms cuối của bản gốc với đúng các khung người học được căn vào đó."""
    ref = _tail_contour(-10.0)
    own_tail_rises = _crafted(ref_st=ref, user_st=_tail_contour(10.0))
    aligned_same = replace(own_tail_rises, user_st_on_ref=ref.copy())
    aligned_rises = replace(own_tail_rises, user=_feats(ref.copy(), _db()))

    assert final_contour(aligned_same) is None
    assert final_contour(aligned_rises) is not None


def test_final_contour_is_still_allowed_when_the_alignment_is_not_ok() -> None:
    inp = _crafted(ref_st=_tail_contour(-10.0), user_st=_tail_contour(10.0), allowed=False)

    assert final_contour(inp) is not None
    assert [r.issue["code"] for r in run_rules(inp)] == ["FINAL_CONTOUR"]


# PITCH_DEVIATION ---------------------------------------------------------------------------


def _raised(delta: float, start: int, end: int) -> np.ndarray:
    user = _wave()
    user[start:end] += delta
    return user


def test_pitch_deviation_fires_on_a_consistent_word_offset_above_three_semitones() -> None:
    inp = _crafted(ref_st=_wave(), user_st=_raised(5.0, 53, 93))

    found = pitch_deviation(inp)

    assert [f.issue for f in found] == [
        {"code": "PITCH_DEVIATION", "wordIndex": 1, "data": {"meanDiffSt": 5.0}}
    ]
    assert found[0].severity == pytest.approx(5.0)


def test_pitch_deviation_reports_the_sign_of_a_lower_word() -> None:
    inp = _crafted(ref_st=_wave(), user_st=_raised(-4.2, 96, 136))

    found = pitch_deviation(inp)

    assert [(f.issue["wordIndex"], f.issue["data"]["meanDiffSt"]) for f in found] == [(2, -4.2)]


def test_pitch_deviation_is_ordered_by_word_index() -> None:
    user = _raised(4.0, 139, 179)
    user[10:50] += 4.0
    found = pitch_deviation(_crafted(ref_st=_wave(), user_st=user))

    assert [f.issue["wordIndex"] for f in found] == [0, 3]


def test_pitch_deviation_ignores_two_semitones_and_a_whole_sentence_shift() -> None:
    assert pitch_deviation(_crafted(ref_st=_wave(), user_st=_raised(2.5, 53, 93))) == []
    assert pitch_deviation(_crafted(ref_st=_wave(), user_st=_wave() + 4.0)) == []


def test_pitch_deviation_needs_frames_in_common_and_a_consistent_sign() -> None:
    few = _raised(5.0, 53, 93)
    few[61:93] = np.nan  # còn 8 khung chung (< PD_MIN_FRAMES)
    ratio = _raised(5.0, 53, 93)
    ratio[68:93] = np.nan  # còn 15 khung chung nhưng < 0.5 độ dài từ (40 khung)
    mixed = _wave()
    mixed[53:78] += 5.0  # 25/40 khung lệch, 15 khung không lệch: nhất quán dấu < 0.8

    assert pitch_deviation(_crafted(ref_st=_wave(), user_st=few)) == []
    assert pitch_deviation(_crafted(ref_st=_wave(), user_st=ratio)) == []
    assert pitch_deviation(_crafted(ref_st=_wave(), user_st=mixed)) == []


def test_pitch_deviation_is_dropped_when_the_alignment_is_not_ok() -> None:
    inp = _crafted(ref_st=_wave(), user_st=_raised(5.0, 53, 93), allowed=False)

    assert pitch_deviation(inp) == []


# EXTRA_PAUSE -------------------------------------------------------------------------------


def _paused(
    at_row: int, extra: int, *, ref_silent: list[tuple[int, int]] | None = None
) -> RuleInput:
    """Người học chèn `extra` khung lặng ngay sau khung `at_row` của bản gốc (path giữ hàng đó)."""
    ref_db = _db(silent=ref_silent)
    user_db = np.concatenate([ref_db[: at_row + 1], np.full(extra, -80.0), ref_db[at_row + 1 :]])
    rows = np.concatenate([np.arange(_N), np.full(extra, at_row)])
    cols = np.arange(_N + extra)
    order = np.argsort(rows, kind="stable")
    path = np.stack([rows[order], cols], axis=1).astype(np.int64)
    user_st = np.zeros(_N + extra)
    return _crafted(ref_db=ref_db, user_db=user_db, user_st=user_st, path=path)


def test_extra_pause_fires_when_the_pause_sits_at_a_word_end() -> None:
    found = extra_pause(_paused(at_row=51, extra=30))

    assert len(found) == 1
    issue = found[0].issue
    assert issue["code"] == "EXTRA_PAUSE" and issue["wordIndex"] == 0
    assert issue["data"]["userMs"] >= 300 and issue["data"]["refMs"] < 100
    assert found[0].severity == pytest.approx(issue["data"]["userMs"])


def test_extra_pause_stays_silent_when_it_maps_far_from_any_word_end() -> None:
    # Cắm 30 khung lặng vào giữa từ "bravo": tâm ánh xạ cách đuôi từ gần nhất > 100 ms.
    assert extra_pause(_paused(at_row=72, extra=30)) == []


def test_extra_pause_stays_silent_when_the_original_pauses_there_too() -> None:
    assert extra_pause(_paused(at_row=51, extra=30, ref_silent=[(50, 66)])) == []


def test_extra_pause_stays_silent_for_a_pause_shorter_than_the_user_minimum() -> None:
    assert extra_pause(_paused(at_row=51, extra=10)) == []


def test_extra_pause_never_names_the_last_word() -> None:
    assert extra_pause(_paused(at_row=196, extra=30)) == []


def test_extra_pause_is_dropped_when_the_alignment_is_not_ok() -> None:
    assert extra_pause(replace(_paused(at_row=51, extra=30), word_issues_allowed=False)) == []


# STRESS_MISMATCH ---------------------------------------------------------------------------


def _prom(*values: float) -> np.ndarray:
    return np.array(values, dtype=np.float64)


def test_stress_mismatch_fires_when_the_tops_differ_by_a_margin_on_both_sides() -> None:
    inp = _crafted(
        ref_prom=_prom(0.0, 2.0, 0.5, 0.0, -1.0), user_prom=_prom(0.0, 0.3, 0.2, 1.9, -1.0)
    )

    found = stress_mismatch(inp)

    assert found is not None
    assert found.issue == {
        "code": "STRESS_MISMATCH",
        "wordIndex": 1,
        "data": {"refWord": "bravo", "userWord": "delta"},
    }
    assert found.severity == pytest.approx(1.5)  # min(margin bản gốc 1.5, margin người học 1.6)


@pytest.mark.parametrize(
    ("ref_prom", "user_prom"),
    [
        (_prom(0.0, 0.4, 0.0, 0.0, -1.0), _prom(0.0, 0.0, 0.0, 2.0, -1.0)),  # margin gốc 0.4 < 0.5
        (_prom(0.0, 2.0, 0.0, 0.0, -1.0), _prom(0.0, 0.0, 0.0, 0.45, -1.0)),  # margin học 0.45
        (_prom(0.0, 2.0, 0.0, 0.0, -1.0), _prom(0.0, 1.8, 0.0, 0.0, -1.0)),  # cùng từ nổi nhất
    ],
)
def test_stress_mismatch_stays_silent_below_the_margin_or_when_the_tops_agree(
    ref_prom: np.ndarray, user_prom: np.ndarray
) -> None:
    assert stress_mismatch(_crafted(ref_prom=ref_prom, user_prom=user_prom)) is None


def test_stress_mismatch_ignores_words_without_a_prominence_value() -> None:
    nan = float("nan")
    # Từ 1 là NaN ở người học: không xếp hạng, nên chỉ còn 4 từ chung (< STRESS_MIN_WORDS).
    inp = _crafted(
        ref_prom=_prom(0.0, 2.0, 0.5, 0.0, -1.0), user_prom=_prom(0.0, nan, 0.2, 1.9, -1.0)
    )

    assert stress_mismatch(inp) is None


def test_stress_mismatch_needs_a_sentence_of_at_least_five_words() -> None:
    inp = replace(
        _crafted(),
        words=_WORDS[:4],
        ref_word_frames=_FRAMES[:4],
        user_word_frames=_FRAMES[:4],
        ref_prominence=_prom(0.0, 2.0, 0.5, 0.0),
        user_prominence=_prom(0.0, 0.3, 0.2, 1.9),
    )

    assert stress_mismatch(inp) is None


def test_stress_mismatch_is_dropped_when_the_alignment_is_not_ok() -> None:
    inp = _crafted(
        ref_prom=_prom(0.0, 2.0, 0.5, 0.0, -1.0),
        user_prom=_prom(0.0, 0.3, 0.2, 1.9, -1.0),
        allowed=False,
    )

    assert stress_mismatch(inp) is None


def test_run_rules_emits_in_the_fixed_order_and_by_word_index_inside_a_code() -> None:
    user = _raised(4.0, 139, 179)
    user[10:50] += 4.0
    inp = _crafted(
        ref_st=_tail_contour(-10.0) + _wave(),
        user_st=_tail_contour(10.0) + user,
        ref_prom=_prom(0.0, 2.0, 0.5, 0.0, -1.0),
        user_prom=_prom(0.0, 0.3, 0.2, 1.9, -1.0),
    )

    codes = [(r.issue["code"], r.issue.get("wordIndex")) for r in run_rules(inp)]

    assert codes == [
        ("STRESS_MISMATCH", 1),
        ("FINAL_CONTOUR", None),
        ("PITCH_DEVIATION", 0),
        ("PITCH_DEVIATION", 3),
    ]


# Phần 2: tín hiệu tổng hợp qua score_prosody ------------------------------------------------


def _codes(score: ProsodyScore) -> list[str]:
    return [str(i["code"]) for i in score.issues]


def _issue(score: ProsodyScore, code: str) -> dict[str, Any]:
    (found,) = [i for i in score.issues if i["code"] == code]
    return found


def _forced_not_ok(ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment:
    n_ref, n_user = len(ref_mfcc), len(user_mfcc)
    return Alignment(linear_path(n_ref, n_user), float("inf"), n_user / n_ref, False, True)


def _rising_end() -> list[SynthWord]:
    last = DEFAULT_WORDS[-1]
    return [
        *DEFAULT_WORDS[:-1],
        SynthWord(last.text, last.dur_s, last.f0_end, last.f0_start, last.formants),
    ]


def test_synthetic_pause_after_word_zero_is_an_extra_pause(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    user, _ = synth_sentence(DEFAULT_WORDS, extra_gap_after={0: 0.5}, seed=1)
    issue = _issue(_score(reference, user), "EXTRA_PAUSE")

    assert issue["wordIndex"] == 0
    assert issue["data"]["userMs"] >= 450
    assert issue["data"]["refMs"] < 100


def test_synthetic_pause_that_also_exists_in_the_original_is_not_flagged() -> None:
    audio, marks = synth_sentence(DEFAULT_WORDS, extra_gap_after={0: 0.5})
    ref_feats = prepare_features(audio)
    user, _ = synth_sentence(DEFAULT_WORDS, extra_gap_after={0: 0.5}, seed=1)

    score = score_prosody(ref_feats, prepare_features(user), _words(marks))

    assert "EXTRA_PAUSE" not in _codes(score)


def test_synthetic_reversed_final_glide_is_a_final_contour_issue(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    user, _ = synth_sentence(_rising_end(), seed=2)
    issue = _issue(_score(reference, user), "FINAL_CONTOUR")

    assert issue["data"]["refSlope"] < 0 < issue["data"]["userSlope"]
    for slope in (issue["data"]["refSlope"], issue["data"]["userSlope"]):
        assert 6.0 <= abs(slope) <= 30.0


def test_synthetic_four_semitones_on_one_word_is_a_pitch_deviation(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    user, _ = synth_sentence(DEFAULT_WORDS, word_f0_offset_st={2: 4.0}, seed=3)
    issue = _issue(_score(reference, user), "PITCH_DEVIATION")

    assert issue["wordIndex"] == 2
    assert issue["data"]["meanDiffSt"] > 3.0


def test_synthetic_two_semitones_or_a_whole_sentence_shift_is_not_a_pitch_deviation(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    two, _ = synth_sentence(DEFAULT_WORDS, word_f0_offset_st={2: 2.0}, seed=3)
    shifted, _ = synth_sentence(DEFAULT_WORDS, f0_scale=2 ** (4 / 12), seed=5)

    assert "PITCH_DEVIATION" not in _codes(_score(reference, two))
    assert _score(reference, shifted).issues == []


def test_synthetic_swapped_prominence_is_a_stress_mismatch() -> None:
    boosted_1 = {"word_f0_offset_st": {1: 5.0}, "word_level_db": {1: 6.0}}
    boosted_3 = {"word_f0_offset_st": {3: 6.0}, "word_level_db": {3: 6.0}}
    audio, marks = synth_sentence(DEFAULT_WORDS, **boosted_1)
    user, _ = synth_sentence(DEFAULT_WORDS, seed=7, **boosted_3)

    score = score_prosody(prepare_features(audio), prepare_features(user), _words(marks))
    issue = _issue(score, "STRESS_MISMATCH")

    assert issue["wordIndex"] == 1
    assert issue["data"] == {"refWord": "bravo", "userWord": "delta"}


def test_synthetic_same_stress_pattern_is_not_a_stress_mismatch() -> None:
    boosted = {"word_f0_offset_st": {1: 5.0}, "word_level_db": {1: 6.0}}
    audio, marks = synth_sentence(DEFAULT_WORDS, **boosted)
    user, _ = synth_sentence(DEFAULT_WORDS, seed=8, **boosted)

    score = score_prosody(prepare_features(audio), prepare_features(user), _words(marks))

    assert "STRESS_MISMATCH" not in _codes(score)


def test_synthetic_flat_learner_has_exactly_one_issue(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)

    assert _codes(_score(reference, flat)) == ["FLAT_PITCH"]


def test_a_flat_original_never_yields_flat_pitch() -> None:
    audio, marks = synth_sentence(DEFAULT_WORDS, flat_f0=180.0)
    flat_user, _ = synth_sentence(DEFAULT_WORDS, flat_f0=185.0, seed=4)

    score = score_prosody(prepare_features(audio), prepare_features(flat_user), _words(marks))

    assert "FLAT_PITCH" not in _codes(score)


def test_unreliable_alignment_keeps_only_sentence_level_rules(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    """D-02: cùng nhiễu loạn, căn bị ép "kém" -> chỉ FLAT_PITCH / FINAL_CONTOUR có thể xuất hiện."""
    _, marks, ref_feats = reference
    boosted = {"word_f0_offset_st": {3: 6.0}, "word_level_db": {3: 6.0}}
    users = [
        synth_sentence(DEFAULT_WORDS, extra_gap_after={0: 0.5}, seed=1)[0],
        synth_sentence(DEFAULT_WORDS, word_f0_offset_st={2: 4.0}, seed=3)[0],
        synth_sentence(DEFAULT_WORDS, seed=7, **boosted)[0],
        synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)[0],
        synth_sentence(_rising_end(), seed=2)[0],
    ]
    seen: set[str] = set()
    for user in users:
        score = score_prosody(
            ref_feats, prepare_features(user), _words(marks), aligner=_forced_not_ok
        )
        assert not score.word_issues_allowed
        seen.update(_codes(score))

    assert seen <= {"FLAT_PITCH", "FINAL_CONTOUR"}
    assert {"FLAT_PITCH", "FINAL_CONTOUR"} <= seen, "rule mức câu vẫn chạy khi căn kém"

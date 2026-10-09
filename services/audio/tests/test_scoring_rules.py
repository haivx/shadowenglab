"""Rule engine Lớp C trên tín hiệu tổng hợp (03-06, RUL-01, D-12).

Không có audio thật trong repo: mọi tín hiệu từ `synth.py`. Các cổng chắc chắn được thử trực tiếp
trên `RuleInput` dựng tay để không phụ thuộc vào chi tiết của F0/DTW.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from synth import DEFAULT_WORDS, synth_sentence

from audio_service.contracts_gen import ScoreResult
from audio_service.rules.engine import RuleInput, flat_pitch, run_rules
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

"""Tracer chấm ngữ điệu (03-03): hai mảng audio tổng hợp -> ScoreResult hợp lệ, tự so = 1.0.

Không có audio thật trong repo: mọi tín hiệu từ `synth.py` (xác định theo seed).
"""

from __future__ import annotations

import math
import re
import time
from pathlib import Path

import numpy as np
import pytest
from synth import DEFAULT_WORDS, SynthWord, synth_sentence

from audio_service.contracts_gen import ScoreResult
from audio_service.scoring import align as align_module
from audio_service.scoring import scorer
from audio_service.scoring.align import Alignment, linear_path
from audio_service.scoring.features import ProsodyFeatures, prepare_features
from audio_service.scoring.scorer import ProsodyScore, RefWord, score_prosody, to_score_result
from audio_service.scoring.thresholds import (
    ALIGN_RATIO_MAX,
    SCORER_VERSION,
    THRESHOLDS_VERSION,
)

Marks = list[tuple[str, float, float]]


@pytest.fixture(scope="module")
def reference() -> tuple[np.ndarray, Marks, ProsodyFeatures]:
    audio, marks = synth_sentence(DEFAULT_WORDS)
    return audio, marks, prepare_features(audio)


def _words(marks: Marks) -> list[RefWord]:
    return [RefWord(text=t, start_s=s, end_s=e) for t, s, e in marks]


@pytest.fixture(scope="module")
def self_score(reference: tuple[np.ndarray, Marks, ProsodyFeatures]) -> ProsodyScore:
    _, marks, feats = reference
    return score_prosody(feats, feats, _words(marks))


def test_self_compare_gives_one_on_every_index(self_score: ProsodyScore) -> None:
    for name in ("speed", "pitch_range", "melody_match", "intonation", "rhythm", "overall"):
        assert getattr(self_score, name) == pytest.approx(1.0, abs=1e-6), name
    assert self_score.alignment.ok
    assert self_score.word_issues_allowed


def test_self_compare_result_validates_against_generated_model(self_score: ProsodyScore) -> None:
    result = to_score_result(
        self_score,
        lesson_id="01TESTLESSON",
        segment_index=3,
        attempt=1,
        timing_ms={"align": 1.0, "metrics": 2.0, "rules": 0.0},
    )

    assert isinstance(result, ScoreResult)
    assert result.versions.scorer == SCORER_VERSION
    assert result.versions.thresholds == THRESHOLDS_VERSION
    assert result.mode == "full"
    assert result.scores.sound is None
    assert result.scores.overall == pytest.approx(1.0, abs=1e-6)
    assert result.scores.intonation == pytest.approx(1.0, abs=1e-6)
    assert result.scores.rhythm == pytest.approx(1.0, abs=1e-6)
    assert len(result.words) == 5
    assert [w.text for w in result.words] == [w.text for w in DEFAULT_WORDS]
    for word in result.words:
        assert word.status == "scored"
        assert word.start <= word.end
        assert word.similarity == pytest.approx(1.0, abs=1e-6)
    assert result.issues == []
    assert result.tips == []


def test_contour_is_aligned_rounded_and_has_increasing_word_bounds(
    self_score: ProsodyScore,
) -> None:
    result = to_score_result(
        self_score, lesson_id="01TESTLESSON", segment_index=0, attempt=1, timing_ms={"align": 0.0}
    )
    contour = result.prosody.contour

    assert len(contour.ref) == len(contour.user) > 50
    assert any(v is None for v in contour.ref), "frame vô thanh phải là null"
    assert any(v is not None for v in contour.ref)
    for value in (*contour.ref, *contour.user):
        if value is not None:
            assert round(value, 1) == pytest.approx(value, abs=1e-9)
    bounds = [b.root for b in contour.word_bounds]
    assert len(bounds) == 5
    assert bounds == sorted(set(bounds)), "wordBounds phải tăng chặt"
    assert bounds[-1] < len(contour.ref)


def test_scoring_package_never_imports_a_model() -> None:
    package = Path(scorer.__file__).parent
    pattern = re.compile(r"^\s*(import|from)\s+(torch|transformers)\b|model_gate", re.MULTILINE)
    for source in package.glob("*.py"):
        assert not pattern.search(source.read_text(encoding="utf-8")), source.name


# --- Bất biến trên tín hiệu tổng hợp (Task 2) ------------------------------------------------

DIFFERENT_SENTENCE = (
    SynthWord("one", 0.26, 190, 175, (350, 2500)),
    SynthWord("two", 0.34, 170, 200, (900, 1300)),
    SynthWord("three", 0.24, 205, 195, (450, 950)),
    SynthWord("four", 0.30, 180, 190, (650, 2000)),
    SynthWord("five", 0.28, 185, 215, (300, 1800)),
    SynthWord("six", 0.30, 190, 250, (500, 1100)),  # câu khác hẳn, cuối câu đi lên
)


def _score_user(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures], user_audio: np.ndarray
) -> ProsodyScore:
    _, marks, ref_feats = reference
    return score_prosody(ref_feats, prepare_features(user_audio), _words(marks))


def test_signal_level_does_not_change_the_score(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    quiet, _ = synth_sentence(DEFAULT_WORDS, level=0.1)

    assert _score_user(reference, quiet).overall >= 0.99


def test_leading_and_trailing_silence_does_not_change_the_score(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    padded, _ = synth_sentence(DEFAULT_WORDS, lead_s=0.6, tail_s=0.5, seed=1)

    assert _score_user(reference, padded).overall >= 0.99


def test_slower_learner_lowers_speed_but_keeps_the_melody(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    slow, _ = synth_sentence(DEFAULT_WORDS, dur_scale=1.3, seed=2)
    score = _score_user(reference, slow)

    assert 0.70 <= score.speed <= 0.85
    assert score.melody_match >= 0.8
    assert score.alignment.ok


def test_higher_pitched_learner_is_not_penalised_for_a_different_voice(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    high, _ = synth_sentence(DEFAULT_WORDS, f0_scale=1.5, seed=3)

    assert _score_user(reference, high).overall >= 0.85


def test_flat_learner_has_a_low_pitch_range(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    score = _score_user(reference, flat)

    assert score.pitch_range <= 0.4
    assert score.overall < 0.6


def test_different_sentence_is_not_aligned_and_scores_low(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    other, _ = synth_sentence(DIFFERENT_SENTENCE, seed=6)
    score = _score_user(reference, other)

    assert not score.alignment.ok
    assert score.alignment.linear
    assert not score.word_issues_allowed
    assert score.overall <= 0.6  # tiêu chí D-a của 03-01 mục D
    assert len(score.words) == 5, "câu vẫn hiển thị được dù căn kém (D-02)"


def test_length_ratio_outside_range_never_builds_a_dtw_matrix(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures], monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("dtw_slack không được gọi khi tỉ lệ độ dài ngoài khoảng")

    monkeypatch.setattr(align_module, "dtw_slack", forbidden)
    slow, _ = synth_sentence(DEFAULT_WORDS, dur_scale=2.6, seed=7)
    score = _score_user(reference, slow)

    assert score.alignment.ratio > ALIGN_RATIO_MAX
    assert score.alignment.linear and not score.alignment.ok
    assert not score.word_issues_allowed
    assert score.melody_match >= 0.8, "melodyMatch tính trên đường tỉ lệ thời gian (D-02)"
    assert score.speed < 0.5, "speed vẫn được tính ở nhánh căn kém"


def test_silent_learner_does_not_raise_and_has_no_melody(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    silent = np.zeros(len(reference[0]), dtype=np.float32)
    score = _score_user(reference, silent)

    assert score.melody_match == 0.0
    assert score.pitch_range == 0.0
    result = to_score_result(
        score, lesson_id="01TESTLESSON", segment_index=0, attempt=1, timing_ms={"align": 0.0}
    )
    assert result.scores.overall == pytest.approx(score.overall)


def test_empty_learner_audio_does_not_raise(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    score = _score_user(reference, np.zeros(0, dtype=np.float32))

    assert score.melody_match == 0.0
    assert not score.alignment.ok
    assert all(math.isfinite(w["start"]) and math.isfinite(w["end"]) for w in score.words)


def test_every_value_in_the_result_is_finite_and_in_range(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    other, _ = synth_sentence(DIFFERENT_SENTENCE, seed=6)
    for user_audio in (other, np.zeros(16000, dtype=np.float32)):
        score = _score_user(reference, user_audio)
        for name in ("speed", "pitch_range", "melody_match", "intonation", "rhythm", "overall"):
            assert 0.0 <= getattr(score, name) <= 1.0, name
        for word in score.words:
            assert 0.0 <= word["similarity"] <= 1.0
            assert 0.0 <= word["start"] <= word["end"]


def test_scores_follow_the_d04_composition(
    reference: tuple[np.ndarray, Marks, ProsodyFeatures],
) -> None:
    slow, _ = synth_sentence(DEFAULT_WORDS, dur_scale=1.3, seed=2)
    score = _score_user(reference, slow)

    assert score.intonation == pytest.approx((score.pitch_range + score.melody_match) / 2)
    assert score.rhythm == pytest.approx(score.speed)
    assert score.overall == pytest.approx(
        (score.speed + score.pitch_range + score.melody_match) / 3
    )


def test_the_aligner_is_swappable(reference: tuple[np.ndarray, Marks, ProsodyFeatures]) -> None:
    calls: list[tuple[int, int]] = []

    def identity_aligner(ref_mfcc: np.ndarray, user_mfcc: np.ndarray) -> Alignment:
        calls.append((len(ref_mfcc), len(user_mfcc)))
        path = linear_path(len(ref_mfcc), len(user_mfcc))
        return Alignment(path=path, cost=0.0, ratio=1.0, ok=True, linear=True)

    _, marks, ref_feats = reference
    score = score_prosody(ref_feats, ref_feats, _words(marks), aligner=identity_aligner)

    assert calls == [(len(ref_feats.mfcc), len(ref_feats.mfcc))]
    assert score.overall == pytest.approx(1.0, abs=1e-6)


def test_scoring_an_eight_second_recording_fits_the_time_headroom() -> None:
    ref_words = tuple(
        SynthWord(f"w{i}", 0.65, 150 + 12 * (i % 5), 190 + 9 * (i % 4), (500 + 40 * i, 1500))
        for i in range(10)
    )
    ref_audio, marks = synth_sentence(ref_words, lead_s=0.6, tail_s=0.5)
    user_audio, _ = synth_sentence(ref_words, lead_s=0.7, tail_s=0.6, seed=9)
    assert len(ref_audio) / 16000 >= 7.5
    ref_feats = prepare_features(ref_audio)

    started = time.perf_counter()
    score = score_prosody(ref_feats, prepare_features(user_audio), _words(marks))
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    assert elapsed_ms < 1500.0
    assert score.overall >= 0.95
    assert set(score.timing_ms) == {"align", "metrics", "rules"}
    assert all(v >= 0.0 for v in score.timing_ms.values())

"""Tracer chấm ngữ điệu (03-03): hai mảng audio tổng hợp -> ScoreResult hợp lệ, tự so = 1.0.

Không có audio thật trong repo: mọi tín hiệu từ `synth.py` (xác định theo seed).
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest
from synth import DEFAULT_WORDS, synth_sentence

from audio_service.contracts_gen import ScoreResult
from audio_service.scoring import scorer
from audio_service.scoring.features import ProsodyFeatures, prepare_features
from audio_service.scoring.scorer import ProsodyScore, RefWord, score_prosody, to_score_result
from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION

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

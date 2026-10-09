"""Ghép điểm ngữ điệu thành ScoreResult (khung RED của 03-03: giao diện có mặt, chưa có hành vi)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from audio_service.contracts_gen import ScoreResult
from audio_service.scoring.align import Aligner, Alignment, align
from audio_service.scoring.features import ProsodyFeatures


@dataclass(frozen=True)
class RefWord:
    text: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class ProsodyScore:
    speed: float
    pitch_range: float
    melody_match: float
    intonation: float
    rhythm: float
    overall: float
    words: list[dict[str, Any]]
    contour: dict[str, Any]
    stress: list[dict[str, Any]]
    pauses: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    tips: list[dict[str, Any]]
    alignment: Alignment
    word_issues_allowed: bool
    ref_word_frames: list[tuple[int, int]]
    timing_ms: dict[str, float] = field(default_factory=dict)


def score_prosody(
    ref: ProsodyFeatures,
    user: ProsodyFeatures,
    ref_words: Sequence[RefWord],
    *,
    aligner: Aligner = align,
) -> ProsodyScore:
    alignment = aligner(ref.mfcc, user.mfcc)
    return ProsodyScore(
        speed=0.0,
        pitch_range=0.0,
        melody_match=0.0,
        intonation=0.0,
        rhythm=0.0,
        overall=0.0,
        words=[],
        contour={"ref": [], "user": [], "wordBounds": []},
        stress=[],
        pauses=[],
        issues=[],
        tips=[],
        alignment=alignment,
        word_issues_allowed=False,
        ref_word_frames=[],
    )


def to_score_result(
    score: ProsodyScore,
    *,
    lesson_id: str,
    segment_index: int,
    attempt: int,
    timing_ms: Mapping[str, float],
) -> ScoreResult:
    raise NotImplementedError

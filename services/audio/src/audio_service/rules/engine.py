"""Rule engine Lớp C (khung RED của 03-06: chưa có rule nào)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_service.scoring.align import Alignment
from audio_service.scoring.features import ProsodyFeatures


@dataclass(frozen=True)
class RuleIssue:
    """`issue` là dict camelCase của `Issue` (score.ts); `severity` dùng để chọn tip (D-14)."""

    issue: dict[str, Any]
    severity: float


@dataclass(frozen=True)
class RuleInput:
    ref: ProsodyFeatures
    user: ProsodyFeatures
    alignment: Alignment
    words: list[str]
    ref_word_frames: list[tuple[int, int]]
    user_word_frames: list[tuple[int, int]]
    user_st_on_ref: np.ndarray
    pitch_range: float
    ref_prominence: np.ndarray
    user_prominence: np.ndarray
    word_issues_allowed: bool


def flat_pitch(inp: RuleInput) -> RuleIssue | None:
    return None


def run_rules(inp: RuleInput) -> list[RuleIssue]:
    return []

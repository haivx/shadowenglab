"""Tách câu từ danh sách từ của Whisper (RED stub: chưa hiện thực)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

SENTENCE_END = (".", "?", "!")
HARD_GAP_S = 0.7
SOFT_GAP_S = 0.25
MAX_DUR_S = 8.0
MAX_WORDS = 15
MIN_DUR_S = 1.5
MAX_MERGED_S = 9.0


@dataclass(frozen=True, slots=True)
class AsrWord:
    text: str
    start: float
    end: float
    probability: float


def split_sentences(words: Sequence[AsrWord]) -> list[tuple[int, int]]:
    return []

"""Khung rỗng để test RED thu thập được (03-11); bản thật ở commit GREEN."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple


class SelfRow(NamedTuple):
    index: int
    text: str
    overall: float
    issues: int
    ms: float


class CrossRow(NamedTuple):
    index: int
    other: int
    overall: float
    align_ok: bool


def verdict(rows: Sequence[SelfRow], cross: Sequence[CrossRow]) -> tuple[str, int]:
    return "SCORE FAILED: chưa hiện thực", 1


def main(argv: list[str] | None = None) -> int:
    return 99

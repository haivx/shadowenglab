"""Tip template tiếng Việt (khung RED của 03-06: chưa chọn tip nào)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from audio_service.rules.engine import RuleIssue

PRIORITY = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")


def render_tip(issue: dict[str, Any], words: Sequence[str]) -> str | None:
    return None


def select_tips(issues: Sequence[RuleIssue], words: Sequence[str]) -> list[dict[str, Any]]:
    return []

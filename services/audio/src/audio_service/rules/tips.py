"""Tip template tiếng Việt và chọn tip theo thứ tự ưu tiên cố định (RUL-02, D-14, D-15).

Hàm thuần. Tip luôn `source: "template"`; mỗi tip trỏ tới một issue cùng mã bằng `issueRef`.
Khen/nhận xét khi không có issue sinh ở client (D-15), nên `select_tips([])` trả `[]`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from audio_service.rules.engine import RuleIssue

PRIORITY = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
MAX_TIPS = 3  # D-14: tối đa 3 tip, mỗi mã tối đa 1

_FLAT_PITCH = "Giọng hơi phẳng; lên xuống rõ hơn theo bản gốc."


def render_tip(issue: dict[str, Any], words: Sequence[str]) -> str | None:
    """Câu gợi ý template cho một issue; None khi không dựng được an toàn."""
    if issue.get("code") == "FLAT_PITCH":
        return _FLAT_PITCH
    return None


def select_tips(issues: Sequence[RuleIssue], words: Sequence[str]) -> list[dict[str, Any]]:
    """Tối đa MAX_TIPS tip theo PRIORITY, mỗi mã một tip lấy issue lệch nhiều nhất (D-14).

    `issueRef` là chỉ số trong `issues` đúng như được truyền vào (không sắp lại, không lọc).
    """
    best: dict[str, tuple[int, str]] = {}
    for index, rule_issue in enumerate(issues):
        code = rule_issue.issue.get("code")
        if code not in PRIORITY:
            continue
        text = render_tip(rule_issue.issue, words)
        if text is None:
            continue
        current = best.get(code)
        if current is None or rule_issue.severity > issues[current[0]].severity:
            best[code] = (index, text)
    tips: list[dict[str, Any]] = []
    for code in PRIORITY:
        if code in best:
            index, text = best[code]
            tips.append({"text": text, "issueRef": index, "source": "template"})
    return tips[:MAX_TIPS]

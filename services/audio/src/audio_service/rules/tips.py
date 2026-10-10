"""Tip template tiếng Việt và chọn tip theo thứ tự ưu tiên cố định (RUL-02, D-14 sửa, D-15, D-16).

Hàm thuần. Tip luôn `source: "template"`; mỗi tip trỏ tới một issue cùng mã bằng `issueRef`.
Khen/nhận xét khi không có issue sinh ở client (D-15, D-15b), nên `select_tips([])` trả `[]`.

D-16: mỗi mã có vài cách nói đã duyệt, số đo lấy từ `issue.data`; cách nói của tip đầu tiên là
`(segment_index + attempt - 1) mod n` nên cùng lượt luôn ra cùng câu, lượt sau đổi câu. Làm tròn
nửa lên (không dùng `round()` của Python vì nó làm tròn về số chẵn: 12.5 % phải hiện 15 %).

Quy ước đánh dấu từ: `*từ*` trong `Tip.text` (client gạch chân, không bao giờ render HTML, 03-08).
Từ lấy từ Whisper hoặc ô "Sửa câu" là dữ liệu không tin cậy (T-03-14): mọi `*` trong từ bị xoá
trước khi chèn vào template, nên từ không thể tự đóng/mở dấu đánh dấu. Lời văn là đề xuất để
Liam duyệt ở PR (P3-G18).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from audio_service.rules.engine import RuleIssue

PRIORITY = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
MAX_TIPS = 3  # D-14 (sửa): tối đa 3 tip

_STRESS_MISMATCH = "Nhấn vào *{ref_word}*, không phải *{user_word}*."
_EXTRA_PAUSE = "Đọc liền qua *{word}*, đừng ngắt ({user_ms} ms)."
_FINAL_FALL = "Xuống giọng ở cuối câu, ở *{last_word}*; bạn đang lên giọng."
_FINAL_RISE = "Lên giọng ở cuối câu, ở *{last_word}*; bạn đang xuống giọng."
_PITCH_HIGH = "Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống."
_PITCH_LOW = "Bạn đang đọc thấp hơn bản gốc ở *{word}*; nâng giọng lên."
_FLAT_PITCH: tuple[str, ...] = (
    "Độ lên xuống của bạn chỉ bằng khoảng {pct}% bản gốc; "
    "mở rộng giọng, lên cao và xuống thấp rõ hơn.",
    "Giọng còn phẳng (khoảng {pct}% độ lên xuống của bản gốc). "
    "Nghe lại bản gốc và bắt chước chỗ giọng vút lên, hạ xuống.",
    "Thử phóng đại ngữ điệu một chút: bạn mới lên xuống được khoảng {pct}% so với bản gốc.",
    'Bản gốc lên xuống nhiều hơn bạn (bạn ≈ {pct}%); đừng ngại đọc hơi "quá", thường sẽ vừa.',
)


def _clean(text: object) -> str | None:
    """Bỏ mọi `*` và khoảng trắng hai đầu; None nếu không còn gì để gạch chân (T-03-14)."""
    if not isinstance(text, str):
        return None
    return text.replace("*", "").strip() or None


def _word_at(words: Sequence[str], index: object) -> str | None:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(words):
        return None
    return _clean(words[index])


def _number(value: object) -> float | None:
    """Số hữu hạn hoặc None: bool, chuỗi, NaN, ±inf đều bị loại (T-03-25)."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _round_half_up(value: float, step: float) -> float:
    """Làm tròn nửa lên tới bội của `step` (12.5 với step 5 -> 15; `round()` sẽ cho 10)."""
    return math.floor(value / step + 0.5) * step


def render_tip(issue: dict[str, Any], words: Sequence[str], *, variant: int = 0) -> str | None:
    """Câu gợi ý template cho một issue; None khi không dựng được an toàn (thiếu từ, dữ liệu lạ).

    Tip chỉ nêu từ mà chính issue chỉ tới (`wordIndex`, `refWord`/`userWord`, từ cuối câu).
    `variant` chọn cách nói (lấy dư theo số cách nói của mã); có dựng được hay không không bao giờ
    phụ thuộc `variant`.
    """
    code = issue.get("code")
    data = issue.get("data")
    if not isinstance(data, dict):
        return None
    if code == "FLAT_PITCH":
        pitch_range = _number(data.get("pitchRange"))
        if pitch_range is None:
            return None
        pct = int(_round_half_up(pitch_range * 100.0, 5.0))
        return _FLAT_PITCH[variant % len(_FLAT_PITCH)].format(pct=pct)
    if code == "STRESS_MISMATCH":
        ref_word, user_word = _clean(data.get("refWord")), _clean(data.get("userWord"))
        if ref_word is None or user_word is None:
            return None
        return _STRESS_MISMATCH.format(ref_word=ref_word, user_word=user_word)
    if code == "EXTRA_PAUSE":
        word, user_ms = _word_at(words, issue.get("wordIndex")), _number(data.get("userMs"))
        if word is None or user_ms is None:
            return None
        return _EXTRA_PAUSE.format(word=word, user_ms=int(round(user_ms)))
    if code == "FINAL_CONTOUR":
        ref_slope, user_slope = _number(data.get("refSlope")), _number(data.get("userSlope"))
        last_word = _word_at(words, len(words) - 1)
        if ref_slope is None or user_slope is None or last_word is None:
            return None
        if ref_slope * user_slope >= 0.0:
            return None
        template = _FINAL_FALL if ref_slope < 0.0 else _FINAL_RISE
        return template.format(last_word=last_word)
    if code == "PITCH_DEVIATION":
        word, diff = _word_at(words, issue.get("wordIndex")), _number(data.get("meanDiffSt"))
        if word is None or diff is None or diff == 0.0:
            return None
        return (_PITCH_HIGH if diff > 0.0 else _PITCH_LOW).format(word=word)
    return None


def select_tips(
    issues: Sequence[RuleIssue], words: Sequence[str], *, segment_index: int, attempt: int
) -> list[dict[str, Any]]:
    """Tối đa MAX_TIPS tip theo PRIORITY, mỗi mã một tip lấy issue lệch nhiều nhất (D-14).

    Cách nói của tip là `(segment_index + attempt - 1) mod n` (D-16): cùng câu, cùng lượt thì cùng
    chữ; lượt sau của cùng câu đổi sang cách nói khác.

    `issueRef` là chỉ số trong `issues` đúng như được truyền vào (không sắp lại, không lọc);
    `issues` vẫn chứa đủ mọi issue cho eval và thống kê. Issue không dựng được câu an toàn bị bỏ
    qua, và mã đó dùng issue tốt nhất còn dựng được. Bằng độ lệch thì lấy issue đứng trước.
    """
    base = segment_index + attempt - 1
    best: dict[str, tuple[int, str]] = {}
    for index, rule_issue in enumerate(issues):
        code = rule_issue.issue.get("code")
        if code not in PRIORITY:
            continue
        text = render_tip(rule_issue.issue, words, variant=base)  # None không phụ thuộc variant
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

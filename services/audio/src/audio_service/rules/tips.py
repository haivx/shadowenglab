"""Tip template tiếng Việt và chọn tip theo thứ tự ưu tiên cố định (RUL-02, D-14 sửa, D-15, D-16).

Hàm thuần. Tip luôn `source: "template"`; mỗi tip trỏ tới một issue cùng mã bằng `issueRef`.
Khen/nhận xét khi không có issue sinh ở client (D-15, D-15b), nên `select_tips([])` trả `[]`.

D-16: mỗi mã có vài cách nói đã duyệt, số đo lấy từ `issue.data`; cách nói của tip đầu tiên là
`(segment_index + attempt - 1) mod n` nên cùng lượt luôn ra cùng câu, lượt sau đổi câu. Làm tròn
nửa lên (không dùng `round()` của Python vì nó làm tròn về số chẵn: 12.5 % phải hiện 15 %).

Quy ước đánh dấu từ: `*từ*` trong `Tip.text` (client gạch chân, không bao giờ render HTML, 03-08).
Từ lấy từ Whisper hoặc ô "Sửa câu" là dữ liệu không tin cậy (T-03-14): mọi `*` trong từ bị xoá
trước khi chèn vào template, nên từ không thể tự đóng/mở dấu đánh dấu. Lời văn là đề xuất để
Liam duyệt ở PR (P3-G18). Trong tip STRESS_MISMATCH, dấu đánh dấu thứ hai luôn là từ của người học
(từ đầu và từ thứ ba, nếu có, là từ của bản gốc); client dựa vào đó để chọn màu gạch chân.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from audio_service.rules.engine import RuleIssue

PRIORITY = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
MAX_TIPS = 3  # D-14 (sửa): tối đa 3 tip
MAX_PER_CODE = 2  # D-14 (sửa): tối đa 2 tip cho một mã, và chỉ với mã nói về từng từ
WORD_CODES = ("EXTRA_PAUSE", "PITCH_DEVIATION")  # được tip thứ hai, theo thứ tự PRIORITY

# Lời văn đã duyệt (03-GAP-TIPS-PROPOSAL.md mục A). Phần tử k của bản đề xuất là chỉ số k-1.
_FLAT_PITCH: tuple[str, ...] = (
    "Độ lên xuống của bạn chỉ bằng khoảng {pct}% bản gốc; "
    "mở rộng giọng, lên cao và xuống thấp rõ hơn.",
    "Giọng còn phẳng (khoảng {pct}% độ lên xuống của bản gốc). "
    "Nghe lại bản gốc và bắt chước chỗ giọng vút lên, hạ xuống.",
    "Thử phóng đại ngữ điệu một chút: bạn mới lên xuống được khoảng {pct}% so với bản gốc.",
    'Bản gốc lên xuống nhiều hơn bạn (bạn ≈ {pct}%); đừng ngại đọc hơi "quá", thường sẽ vừa.',
)
_EXTRA_PAUSE: tuple[str, ...] = (
    "Đọc liền qua *{word}*, đừng ngắt ({ms} ms).",
    "Bạn dừng {ms} ms sau *{word}*, bản gốc đọc nối luôn; nối *{word}* với từ sau.",
    "Bỏ khoảng nghỉ sau *{word}* ({ms} ms): giữ hơi và đọc trọn cụm.",
)
_FINAL_FALL: tuple[str, ...] = (
    "Xuống giọng ở cuối câu, ở *{last}*; bạn đang lên giọng.",
    "Cuối câu bản gốc hạ giọng ở *{last}*, còn bạn lại lên nên nghe như đang hỏi. "
    "Kết thúc dứt khoát, hạ xuống.",
    "Ở *{last}*, để giọng rơi xuống như kết thúc một ý, đừng kéo lên.",
)
_FINAL_RISE: tuple[str, ...] = (
    "Lên giọng ở cuối câu, ở *{last}*; bạn đang xuống giọng.",
    "Bản gốc kéo giọng lên ở *{last}* (giọng hỏi hoặc chưa nói hết ý), bạn lại hạ xuống; "
    "kết thúc bằng giọng đi lên.",
    "Ở *{last}*, nâng giọng lên ở cuối như bản gốc thay vì hạ xuống.",
)
_PITCH_HIGH: tuple[str, ...] = (
    "Bạn đang đọc cao hơn bản gốc ở *{word}*; hạ giọng xuống.",
    "*{word}* của bạn cao hơn bản gốc khoảng {st} nửa cung; đọc từ này thấp và nhẹ hơn.",
    "Hạ *{word}* xuống chừng {st} nửa cung cho khớp bản gốc.",
)
_PITCH_LOW: tuple[str, ...] = (
    "Bạn đang đọc thấp hơn bản gốc ở *{word}*; nâng giọng lên.",
    "*{word}* của bạn thấp hơn bản gốc khoảng {st} nửa cung; đẩy giọng lên ở từ này.",
    "Nâng *{word}* lên chừng {st} nửa cung, bản gốc nói từ này cao hơn.",
)
_STRESS_MISMATCH: tuple[str, ...] = (
    "Nhấn vào *{ref}*, không phải *{user}*.",
    "Bản gốc nhấn mạnh nhất ở *{ref}*, bạn lại nhấn *{user}*. "
    "Đọc *{ref}* to, dài và cao hơn một chút.",
    "Dồn trọng âm của câu về *{ref}*; *{user}* nên đọc nhẹ đi.",
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


def _half_steps(value: float) -> str:
    """Độ lệch tuyệt đối làm tròn tới nửa cung, in `3` hoặc `3.5` (dấu chấm như `3.1s` ở design)."""
    rounded = _round_half_up(abs(value), 0.5)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"


def render_tip(issue: dict[str, Any], words: Sequence[str], *, variant: int = 0) -> str | None:
    """Câu gợi ý template cho một issue; None khi không dựng được an toàn (thiếu từ, dữ liệu lạ).

    Tip chỉ nêu từ mà chính issue chỉ tới (`wordIndex`, `refWord`/`userWord`, từ cuối câu).
    `variant` chọn cách nói (lấy dư theo số cách nói của mã/hướng); có dựng được hay không không
    bao giờ phụ thuộc `variant`. Từ chèn vào qua đối số của `str.format`, nên chữ được chèn không
    bao giờ bị đọc lại như một placeholder.
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
        template = _STRESS_MISMATCH[variant % len(_STRESS_MISMATCH)]
        return template.format(ref=ref_word, user=user_word)
    if code == "EXTRA_PAUSE":
        word, user_ms = _word_at(words, issue.get("wordIndex")), _number(data.get("userMs"))
        if word is None or user_ms is None:
            return None
        template = _EXTRA_PAUSE[variant % len(_EXTRA_PAUSE)]
        return template.format(word=word, ms=int(_round_half_up(user_ms, 1.0)))
    if code == "FINAL_CONTOUR":
        ref_slope, user_slope = _number(data.get("refSlope")), _number(data.get("userSlope"))
        last_word = _word_at(words, len(words) - 1)
        if ref_slope is None or user_slope is None or last_word is None:
            return None
        if ref_slope * user_slope >= 0.0:
            return None
        templates = _FINAL_FALL if ref_slope < 0.0 else _FINAL_RISE
        return templates[variant % len(templates)].format(last=last_word)
    if code == "PITCH_DEVIATION":
        word, diff = _word_at(words, issue.get("wordIndex")), _number(data.get("meanDiffSt"))
        if word is None or diff is None or diff == 0.0:
            return None
        templates = _PITCH_HIGH if diff > 0.0 else _PITCH_LOW
        return templates[variant % len(templates)].format(word=word, st=_half_steps(diff))
    return None


def _named_word(issue: dict[str, Any], words: Sequence[str]) -> int | None:
    """Chỉ số từ mà tip của issue gọi tên (để tip thứ hai không nhắc lại cùng một từ)."""
    code = issue.get("code")
    if code == "FINAL_CONTOUR":
        return len(words) - 1
    if code in ("STRESS_MISMATCH", "EXTRA_PAUSE", "PITCH_DEVIATION"):
        index = issue.get("wordIndex")
        if isinstance(index, int) and not isinstance(index, bool):
            return index
    return None


def select_tips(
    issues: Sequence[RuleIssue], words: Sequence[str], *, segment_index: int, attempt: int
) -> list[dict[str, Any]]:
    """Chọn tối đa MAX_TIPS tip theo hai lượt (D-14 sửa), cách nói theo câu và lượt (D-16).

    Lượt 1: mỗi mã một tip, theo PRIORITY, lấy issue lệch nhiều nhất còn dựng được câu an toàn
    (bằng độ lệch thì lấy issue đứng trước). Lượt 2, chỉ khi chưa đủ MAX_TIPS: với EXTRA_PAUSE rồi
    PITCH_DEVIATION, thêm issue lệch nhiều nhất kế tiếp mà từ của nó chưa được tip nào gọi tên;
    mỗi mã tối đa MAX_PER_CODE tip, còn STRESS_MISMATCH, FINAL_CONTOUR, FLAT_PITCH không bao giờ
    có tip thứ hai. Thứ tự trả về: PRIORITY, rồi hạng trong mã.

    Cách nói là `(segment_index + attempt - 1) + hạng` lấy dư: tip đầu của mã dùng đúng công thức
    D-16, tip thứ hai dịch một nấc để hai tip cùng mã trong một lượt không giống nhau (lựa chọn
    của Claude, chờ Liam duyệt ở PR, P3-G18). `issueRef` là chỉ số trong `issues` đúng như được
    truyền vào (không sắp lại, không lọc); `issues` vẫn chứa đủ mọi issue cho eval và thống kê.
    """
    base = segment_index + attempt - 1
    ranked: dict[str, list[int]] = {code: [] for code in PRIORITY}
    for index, rule_issue in enumerate(issues):
        code = rule_issue.issue.get("code")
        if code in ranked and render_tip(rule_issue.issue, words) is not None:
            ranked[code].append(index)
    for indexes in ranked.values():
        indexes.sort(key=lambda i: -issues[i].severity)  # sort ổn định: bằng nhau giữ thứ tự cũ

    chosen: list[tuple[str, int, int]] = [  # (mã, hạng, chỉ số issue)
        (code, 0, ranked[code][0]) for code in PRIORITY if ranked[code]
    ][:MAX_TIPS]
    named = {
        word
        for _, _, index in chosen
        if (word := _named_word(issues[index].issue, words)) is not None
    }
    for code in WORD_CODES:
        if len(chosen) >= MAX_TIPS:
            break
        taken = sum(1 for chosen_code, _, _ in chosen if chosen_code == code)
        if taken == 0 or taken >= MAX_PER_CODE:
            continue
        for index in ranked[code][taken:]:
            word = _named_word(issues[index].issue, words)
            if word is not None and word not in named:
                chosen.append((code, taken, index))
                named.add(word)
                break

    chosen.sort(key=lambda item: (PRIORITY.index(item[0]), item[1]))
    tips: list[dict[str, Any]] = []
    for _, rank, index in chosen:
        text = render_tip(issues[index].issue, words, variant=base + rank)
        if text is not None:  # luôn đúng: đã kiểm dựng được ở trên, và không phụ thuộc variant
            tips.append({"text": text, "issueRef": index, "source": "template"})
    return tips

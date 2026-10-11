"""Đếm TP/FP/FN theo bảng mã D-10 đã duyệt ở 04-01 và khoảng tin cậy Wilson (04-02, EVL-02).

Nguồn sự thật của cách đếm là `04-01-SUMMARY.md` ("Quyết định đã chốt", mục B-C), không phải plan
này. Tóm tắt (w = wordIndex đã khai báo):

- TP: issue mang mã chính của errorType, đúng vị trí (D-08; EXTRA_PAUSE cho lệch +-1 từ). Mỗi case
  tối đa một TP: ứng viên gần w nhất, hoà thì chỉ số từ nhỏ hơn (C1); ứng viên còn lại là FP.
- Mã phụ của errorType (`CODE_TABLE`) và issue khớp `alsoPresent` là trung tính (C2, D-09).
- Mọi issue còn lại là FP, kể cả đúng mã sai từ (C3). Mọi issue trên clip `weak_form`/`final_drop`
  (D-07), clip `correct` (D-18b) và mốc tự so (D-18a) là FP.
- Recall của rule = số case có TP / số case có mã chính đó (C4). Clip không issue, không có tiếng
  hay căn thất bại là FN (D-11b).

Hàm thuần: Observation vào, kết quả ra; không đọc file.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from audio_service.contracts_gen import EvalCase
    from audio_service.scoring.scorer import ProsodyScore
    from evalkit.rescore import ClipInput, SelfInput

# Thứ tự `run_rules` (nền của issueRef).
LAYER_C_CODES = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
POOLED = "GỘP"
ERROR_TYPE_ORDER = (
    "wrong_stress",
    "flat",
    "extra_pause",
    "final_rise",
    "pitch_off",
    "weak_form",
    "final_drop",
)
NEGATIVE_SOURCES = ("correct", "self")

Source = Literal["error", "correct", "self"]
Outcome = Literal["tp", "fp", "secondary", "also"]
Location = Literal["word", "word_pm1", "user_word", "sentence", "any_word", "last_word"]


@dataclass(frozen=True)
class Expectation:
    """Mã Lớp C mong đợi của một errorType: mã chính + vị trí, và các mã phụ (mã, vị trí).

    `location`: `word` = wordIndex bằng w; `word_pm1` = lệch không quá 1 từ (D-08); `user_word` =
    `data.userWord` đúng là chữ của từ w (B1-a); `sentence` = cả câu. Vị trí của mã phụ còn có
    `any_word` (bất kỳ từ) và `last_word` (từ cuối).
    """

    primary: str | None
    location: Location | None
    secondary: tuple[tuple[str, Location], ...]


CODE_TABLE: dict[str, Expectation] = {
    "wrong_stress": Expectation("STRESS_MISMATCH", "user_word", (("PITCH_DEVIATION", "word"),)),
    "pitch_off": Expectation("PITCH_DEVIATION", "word", (("STRESS_MISMATCH", "user_word"),)),
    "extra_pause": Expectation("EXTRA_PAUSE", "word_pm1", ()),
    "flat": Expectation("FLAT_PITCH", "sentence", (("PITCH_DEVIATION", "any_word"),)),
    "final_rise": Expectation("FINAL_CONTOUR", "sentence", (("PITCH_DEVIATION", "last_word"),)),
    # Lớp A, Phase 5: chưa có mã chính, mọi issue Lớp C trên các clip này là FP (D-07).
    "weak_form": Expectation(None, None, ()),
    "final_drop": Expectation(None, None, ()),
}


@dataclass(frozen=True)
class Observation:
    """Một lần chấm: case khai báo gì, scorer báo gì. `source` quyết định cách đếm (D-18)."""

    source: Source
    split: str | None
    lesson_id: str
    segment_index: int
    case_id: str | None
    clip: str | None
    error_type: str | None
    word_index: int | None
    also_present: tuple[tuple[str, int | None], ...]
    words: tuple[str, ...]
    issues: tuple[dict[str, Any], ...]
    align_ok: bool
    voiced: bool
    overall: float


@dataclass(frozen=True)
class Verdict:
    """Kết luận cho một issue: mã, từ, và `outcome`."""

    code: str
    word_index: int | None
    outcome: Outcome
    issue: dict[str, Any]


@dataclass
class RuleTally:
    """TP/FP của một mã; `expected` = số case có mã chính này, `found` = số case có TP (C4)."""

    tp: int = 0
    fp: int = 0
    expected: int = 0
    found: int = 0


@dataclass(frozen=True)
class FpRow:
    """Một FP để Liam nghe lại (D-09): case, clip, điều đã khai báo, issue bị báo."""

    split: str
    case_id: str
    clip: str
    declared: str
    code: str
    word_index: int | None
    word_text: str | None


@dataclass(frozen=True)
class CoverageRow:
    """Số case của một (errorType hoặc `correct`) x split: tổng / đã gắn clip / đã chấm."""

    label: str
    split: str
    total: int
    tagged: int
    scored: int


@dataclass(frozen=True)
class SelfRow:
    """Một câu của mốc tự so: điểm, số issue và mã issue (phải là 0 issue, D-18a)."""

    lesson_id: str
    segment_index: int
    split: str
    voiced: bool
    overall: float
    n_issues: int
    codes: tuple[str, ...]


def observation_from(
    case: EvalCase, clip: ClipInput, score: ProsodyScore | None, *, split: str | None = None
) -> Observation:
    """Dựng Observation từ case và kết quả chấm; `score` None = không có tiếng nên không issue."""
    also = tuple((entry.error_type.root, entry.word_index) for entry in (case.also_present or []))
    return Observation(
        source="error" if case.kind == "error" else "correct",
        split=split if split is not None else case.split,
        lesson_id=case.lesson_id,
        segment_index=case.segment_index,
        case_id=case.case_id,
        clip=case.clip,
        error_type=case.error_type.root if case.error_type is not None else None,
        word_index=case.word_index,
        also_present=also,
        words=tuple(clip.words),
        issues=tuple(score.issues) if score is not None else (),
        align_ok=score.alignment.ok if score is not None else False,
        voiced=score is not None,
        overall=score.overall if score is not None else 0.0,
    )


def self_observation(item: SelfInput, score: ProsodyScore | None) -> Observation:
    """Mốc tự so (D-18a) thành Observation: không có case, mọi issue sẽ là FP."""
    return Observation(
        source="self",
        split=item.split,
        lesson_id=item.lesson_id,
        segment_index=item.segment_index,
        case_id=None,
        clip=None,
        error_type=None,
        word_index=None,
        also_present=(),
        words=tuple(word.text for word in item.ref.words),
        issues=tuple(score.issues) if score is not None else (),
        align_ok=score.alignment.ok if score is not None else False,
        voiced=score is not None,
        overall=score.overall if score is not None else 0.0,
    )


def self_rows(observations: Sequence[Observation]) -> list[SelfRow]:
    """Một dòng mỗi câu tự so, sắp theo (bài, câu)."""
    rows = [
        SelfRow(
            lesson_id=obs.lesson_id,
            segment_index=obs.segment_index,
            split=obs.split or "?",
            voiced=obs.voiced,
            overall=obs.overall,
            n_issues=len(obs.issues),
            codes=tuple(str(issue["code"]) for issue in obs.issues),
        )
        for obs in observations
        if obs.source == "self"
    ]
    return sorted(rows, key=lambda row: (row.lesson_id, row.segment_index))


def _matches(
    location: Location | None,
    issue: dict[str, Any],
    word_index: int | None,
    words: Sequence[str],
) -> bool:
    """Issue ở đúng vị trí `location` so với từ khai báo `word_index` (None = không ràng buộc)."""
    if location is None:
        return False
    if location in ("sentence", "any_word"):
        return True
    at = issue.get("wordIndex")
    if location == "last_word":
        return at is not None and at == len(words) - 1
    if word_index is None:
        return True
    if location == "word":
        return at == word_index
    if location == "word_pm1":
        return at is not None and abs(at - word_index) <= 1
    if location == "user_word":
        user_word = (issue.get("data") or {}).get("userWord")
        return word_index < len(words) and user_word == words[word_index]
    return False


def _distance(issue: dict[str, Any], word_index: int | None) -> int:
    at = issue.get("wordIndex")
    return abs(at - word_index) if at is not None and word_index is not None else 0


def _expectation(obs: Observation) -> Expectation | None:
    if obs.source in NEGATIVE_SOURCES or obs.error_type is None:
        return None
    return CODE_TABLE.get(obs.error_type)


def _also_present(obs: Observation, issue: dict[str, Any]) -> bool:
    """Issue khớp một mục `alsoPresent` (mã chính hoặc mã phụ, cùng quy tắc vị trí) (C2, D-09)."""
    code = issue["code"]
    for error_type, word_index in obs.also_present:
        expected = CODE_TABLE.get(error_type)
        if expected is None:
            continue
        options: list[tuple[str | None, Location | None]] = [(expected.primary, expected.location)]
        options.extend(expected.secondary)
        for option_code, location in options:
            if option_code == code and _matches(location, issue, word_index, obs.words):
                return True
    return False


def classify(obs: Observation) -> list[Verdict]:
    """Phân loại từng issue của một Observation theo C1-C3 (thứ tự trả về = thứ tự issue)."""
    expected = _expectation(obs)
    primary = expected.primary if expected is not None else None
    location = expected.location if expected is not None else None

    chosen: int | None = None
    if primary is not None:
        candidates = [
            (position, issue)
            for position, issue in enumerate(obs.issues)
            if issue["code"] == primary and _matches(location, issue, obs.word_index, obs.words)
        ]
        if candidates:
            chosen = min(
                candidates,
                key=lambda item: (
                    _distance(item[1], obs.word_index),
                    item[1].get("wordIndex") or 0,
                    item[0],
                ),
            )[0]

    verdicts: list[Verdict] = []
    for position, issue in enumerate(obs.issues):
        code = str(issue["code"])
        outcome: Outcome
        if position == chosen:
            outcome = "tp"
        elif code == primary and _matches(location, issue, obs.word_index, obs.words):
            outcome = "fp"  # C1: ứng viên thừa của mã chính
        elif expected is not None and any(
            code == sec_code and _matches(sec_location, issue, obs.word_index, obs.words)
            for sec_code, sec_location in expected.secondary
        ):
            outcome = "secondary"
        elif _also_present(obs, issue):
            outcome = "also"
        else:
            outcome = "fp"
        verdicts.append(Verdict(code, issue.get("wordIndex"), outcome, issue))
    return verdicts


def tally(observations: Sequence[Observation]) -> dict[str, RuleTally]:
    """TP/FP/expected/found theo mã, cộng dòng `POOLED` gộp mọi mã Lớp C (C4)."""
    result: dict[str, RuleTally] = defaultdict(RuleTally)
    for code in LAYER_C_CODES:
        result[code] = RuleTally()
    for obs in observations:
        verdicts = classify(obs)
        for verdict in verdicts:
            if verdict.outcome == "tp":
                result[verdict.code].tp += 1
            elif verdict.outcome == "fp":
                result[verdict.code].fp += 1
        expected = _expectation(obs)
        if expected is not None and expected.primary is not None:
            result[expected.primary].expected += 1
            if any(v.outcome == "tp" for v in verdicts):
                result[expected.primary].found += 1
    pooled = RuleTally()
    for code in LAYER_C_CODES:
        pooled.tp += result[code].tp
        pooled.fp += result[code].fp
        pooled.expected += result[code].expected
        pooled.found += result[code].found
    result[POOLED] = pooled
    return dict(result)


def _label(obs: Observation) -> str:
    """Nhãn nhóm của một Observation: errorType, `correct` hoặc `self`."""
    return obs.error_type if obs.source == "error" and obs.error_type else obs.source


def align_failures(observations: Sequence[Observation]) -> dict[tuple[str, str], tuple[int, int]]:
    """(thất bại, tổng) theo (lessonId, errorType | correct | self); thất bại = căn không ok."""
    counts: dict[tuple[str, str], list[int]] = {}
    for obs in observations:
        failed_total = counts.setdefault((obs.lesson_id, _label(obs)), [0, 0])
        failed_total[0] += 0 if obs.align_ok else 1
        failed_total[1] += 1
    return {key: (value[0], value[1]) for key, value in counts.items()}


def _declared(obs: Observation) -> str:
    if obs.source != "error" or obs.error_type is None:
        return obs.source
    if obs.word_index is None:
        return obs.error_type
    return f"{obs.error_type}@{obs.word_index}"


def fp_rows(observations: Sequence[Observation]) -> list[FpRow]:
    """Mọi FP trên clip thật (không gồm mốc tự so), sắp theo caseId rồi mã (D-09)."""
    rows: list[FpRow] = []
    for obs in observations:
        if obs.source == "self":
            continue
        for verdict in classify(obs):
            if verdict.outcome != "fp":
                continue
            at = verdict.word_index
            text = obs.words[at] if at is not None and 0 <= at < len(obs.words) else None
            rows.append(
                FpRow(
                    split=obs.split or "?",
                    case_id=obs.case_id or "-",
                    clip=obs.clip or "-",
                    declared=_declared(obs),
                    code=verdict.code,
                    word_index=at,
                    word_text=text,
                )
            )
    return sorted(rows, key=lambda row: (row.case_id, row.code, row.word_index or 0))


def coverage_rows(cases: Sequence[EvalCase], scored_ids: set[str]) -> list[CoverageRow]:
    """Số case theo (errorType | correct) x split: tổng / đã gắn clip / đã chấm (nhóm có case)."""
    groups: dict[tuple[str, str], list[int]] = {}
    for case in cases:
        label = case.error_type.root if case.error_type is not None else "correct"
        counts = groups.setdefault((label, case.split or "chưa chốt"), [0, 0, 0])
        counts[0] += 1
        counts[1] += 1 if case.clip is not None else 0
        counts[2] += 1 if case.case_id in scored_ids else 0
    labels = (*ERROR_TYPE_ORDER, "correct")
    splits = ("tuning", "heldout", "chưa chốt")
    return [
        CoverageRow(label, split, *groups[(label, split)])
        for label in labels
        for split in splits
        if (label, split) in groups
    ]


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    """Khoảng tin cậy Wilson cho tỉ lệ k/n (mặc định 95 %); n = 0 -> None."""
    if n <= 0:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high

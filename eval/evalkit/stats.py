"""Thống kê thuần cho report eval (04-07, EVL-02): test-retest, tất định (D-19), điểm tổng (D-17).

Nguồn sự thật của khoá nhóm và chỉ số là `04-01-SUMMARY.md` mục J, không phải plan này. Tóm tắt:

- Nhóm test-retest = (lessonId, segmentIndex, kind, errorType, wordIndex) có >= 2 clip đã gắn và đã
  chấm trong tập đang chấm. Clip không có tiếng (VAD) không có điểm nên không tham gia.
- Mỗi nhóm in SD mẫu (ddof 1) của overall, speed, pitchRange, melodyMatch và Jaccard trung bình
  (theo cặp) của tập (code, wordIndex) giữa các lượt. Dòng tổng có SD gộp trong nhóm và ICC(1,1) của
  overall khi có >= `RETEST_MIN_GROUPS_FOR_ICC` nhóm.
- Kiểm tất định: chấm lại `DETERMINISM_SAMPLE` clip đầu (theo caseId), overall và issues phải bằng
  nhau tuyệt đối.

Hàm thuần: số liệu vào, kết quả ra; không đọc file, không import `audio_service` lúc chạy.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from audio_service.contracts_gen import EvalCase
    from audio_service.scoring.scorer import ProsodyScore

# 04-01 mục J: ICC(1,1) chỉ tính khi có đủ nhóm; kiểm tất định chấm lại 5 clip đầu theo caseId.
RETEST_MIN_GROUPS_FOR_ICC = 5
DETERMINISM_SAMPLE = 5
# Chỉ số in trong bảng test-retest (thuộc tính của ProsodyScore) và tên cột tương ứng.
RETEST_METRICS = ("overall", "speed", "pitch_range", "melody_match")

GroupKey = tuple[str, int, str, str | None, int | None]


@dataclass(frozen=True)
class ScoredClip:
    """Một clip đã chấm: case và điểm (None = clip không có tiếng)."""

    case: EvalCase
    score: ProsodyScore | None


def sample_sd(values: Sequence[float]) -> float:
    """SD mẫu (ddof 1); 0.0 khi chỉ có một giá trị."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = math.fsum(values) / n
    return math.sqrt(math.fsum((value - mean) ** 2 for value in values) / (n - 1))


def pooled_sd(groups: Sequence[Sequence[float]]) -> float | None:
    """SD gộp trong nhóm: căn của (tổng bình phương lệch trong nhóm) / (tổng (k - 1)).

    None khi không nhóm nào có >= 2 giá trị (mẫu số 0).
    """
    squares = 0.0
    dof = 0
    for group in groups:
        k = len(group)
        if k < 2:
            continue
        mean = math.fsum(group) / k
        squares += math.fsum((value - mean) ** 2 for value in group)
        dof += k - 1
    if dof == 0:
        return None
    return math.sqrt(squares / dof)


def jaccard(a: set[Any], b: set[Any]) -> float:
    """|a ∩ b| / |a ∪ b|; hai tập rỗng giống nhau tuyệt đối nên bằng 1.0."""
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def group_key(case: EvalCase) -> GroupKey:
    """Khoá nhóm test-retest (04-01 mục J)."""
    error_type = case.error_type.root if case.error_type is not None else None
    return (case.lesson_id, case.segment_index, case.kind, error_type, case.word_index)


def _sort_key(key: GroupKey) -> tuple[str, int, str, str, int]:
    lesson_id, segment, kind, error_type, word = key
    return (lesson_id, segment, kind, error_type or "", -1 if word is None else word)


def retest_groups(clips: Iterable[ScoredClip]) -> dict[GroupKey, list[ScoredClip]]:
    """Nhóm các clip CÓ ĐIỂM theo `group_key`, chỉ giữ nhóm >= 2 clip, sắp theo khoá rồi caseId."""
    grouped: dict[GroupKey, list[ScoredClip]] = {}
    for clip in clips:
        if clip.score is None:
            continue
        grouped.setdefault(group_key(clip.case), []).append(clip)
    return {
        key: sorted(grouped[key], key=lambda item: item.case.case_id)
        for key in sorted(grouped, key=_sort_key)
        if len(grouped[key]) >= 2
    }


def issue_set(score: ProsodyScore) -> set[tuple[str, int | None]]:
    """Tập (code, wordIndex) của các issue một lượt chấm."""
    return {(str(issue["code"]), issue.get("wordIndex")) for issue in score.issues}


@dataclass(frozen=True)
class RetestGroup:
    """Một nhóm test-retest: khoá, số clip k, SD từng chỉ số và Jaccard trung bình theo cặp."""

    key: GroupKey
    k: int
    sd: Mapping[str, float]
    jaccard: float
    overalls: tuple[float, ...]


@dataclass(frozen=True)
class RetestSummary:
    """Mọi nhóm test-retest cộng dòng tổng: SD gộp từng chỉ số, Jaccard trung bình, ICC overall."""

    groups: tuple[RetestGroup, ...]
    pooled: Mapping[str, float | None]
    mean_jaccard: float | None
    icc: float | None


def build_retest(clips: Iterable[ScoredClip]) -> RetestSummary:
    """Tính test-retest trên các clip đã chấm (ICC chỉ khi đủ `RETEST_MIN_GROUPS_FOR_ICC` nhóm)."""
    rows: list[RetestGroup] = []
    values: dict[str, list[list[float]]] = {metric: [] for metric in RETEST_METRICS}
    for key, members in retest_groups(clips).items():
        scores = [item.score for item in members if item.score is not None]
        per_metric = {
            metric: [float(getattr(score, metric)) for score in scores] for metric in RETEST_METRICS
        }
        for metric, series in per_metric.items():
            values[metric].append(series)
        sets = [issue_set(score) for score in scores]
        pairs = [jaccard(a, b) for a, b in itertools.combinations(sets, 2)]
        rows.append(
            RetestGroup(
                key=key,
                k=len(scores),
                sd={metric: sample_sd(series) for metric, series in per_metric.items()},
                jaccard=math.fsum(pairs) / len(pairs),
                overalls=tuple(per_metric["overall"]),
            )
        )
    mean_jaccard = math.fsum(row.jaccard for row in rows) / len(rows) if rows else None
    return RetestSummary(
        groups=tuple(rows),
        pooled={metric: pooled_sd(values[metric]) for metric in RETEST_METRICS},
        mean_jaccard=mean_jaccard,
        icc=None,
    )


# --- kiểm tất định -----------------------------------------------------------------------------


def _canonical_issues(issues: Sequence[Mapping[str, Any]]) -> str:
    return json.dumps(list(issues), sort_keys=True, ensure_ascii=False, default=str)


def scores_equal(first: ProsodyScore | None, second: ProsodyScore | None) -> bool:
    """Hai lần chấm giống hệt: `overall` bằng nhau tuyệt đối và issues bằng nhau (JSON chuẩn hoá).

    Cả hai là None (clip không có tiếng ở cả hai lần) cũng là giống nhau.
    """
    if first is None or second is None:
        return first is None and second is None
    same_issues = _canonical_issues(first.issues) == _canonical_issues(second.issues)
    return first.overall == second.overall and same_issues


@dataclass(frozen=True)
class Determinism:
    """Kết quả kiểm tất định: số clip đã chấm lại và caseId lệch (rỗng = PASS)."""

    checked: int
    failed: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failed

"""Ghép điểm ngữ điệu Lớp B thành `ScoreResult` (PRO-02, D-04, D-05, D-06).

Hàm thuần: hai `ProsodyFeatures` + mốc từ của bản gốc vào, `ProsodyScore` ra; không model, không
file. Stress và pauses (prominence), issues (rule Lớp C) do 03-06 điền. Tip (template, D-14 sửa,
D-16) chọn trong `to_score_result`, lúc đã biết số lượt do transaction cấp (C1): cách nói của tip
phụ thuộc câu và lượt.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from audio_service.contracts_gen import ScoreResult
from audio_service.rules.engine import RuleInput, RuleIssue, run_rules
from audio_service.rules.tips import select_tips
from audio_service.scoring import metrics, prominence
from audio_service.scoring.align import Aligner, Alignment, align
from audio_service.scoring.features import HOP_S, ProsodyFeatures
from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION

_CONTOUR_STEP = 2  # contour lấy mẫu mỗi 20 ms


@dataclass(frozen=True)
class RefWord:
    """Một từ của bản gốc: giây tính từ đầu clip bản gốc (chưa cắt lặng)."""

    text: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class ProsodyScore:
    """Kết quả Lớp B. Các dict là dạng camelCase của contract (WordScore, Contour...)."""

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
    rule_issues: list[RuleIssue]
    word_texts: list[str]
    alignment: Alignment
    word_issues_allowed: bool
    ref_word_frames: list[tuple[int, int]]
    timing_ms: dict[str, float] = field(default_factory=dict)


def _unit(value: float) -> float:
    """Hàng rào hữu hạn: NaN/inf -> 0.0, kẹp về [0, 1] (T-03-06)."""
    return min(max(float(value), 0.0), 1.0) if math.isfinite(value) else 0.0


def _ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def score_prosody(
    ref: ProsodyFeatures,
    user: ProsodyFeatures,
    ref_words: Sequence[RefWord],
    *,
    aligner: Aligner = align,
) -> ProsodyScore:
    """Chấm `user` so với `ref` (cùng một người nói gốc). Căn kém: melody theo tỉ lệ thời gian."""
    n_ref = int(ref.f0_st.shape[0])

    started = time.perf_counter()
    alignment = aligner(ref.mfcc, user.mfcc)
    align_ms = _ms(started)

    started = time.perf_counter()
    user_on_ref = metrics.user_on_ref_axis(user.f0_st, alignment.path, n_ref)
    speed = _unit(metrics.speed(ref.energy_db, user.energy_db))
    pitch_range = _unit(metrics.pitch_range(ref.f0_st, user.f0_st))
    melody_match = _unit(metrics.melody_match(ref.f0_st, user_on_ref))
    intonation = _unit((pitch_range + melody_match) / 2.0)
    rhythm = speed
    overall = _unit((speed + pitch_range + melody_match) / 3.0)

    frames = metrics.word_frames(ref_words, ref.trim_start, n_ref)
    offset = metrics.sentence_offset(ref.f0_st, user_on_ref)
    similarity = metrics.word_similarity(ref.f0_st, user_on_ref, frames, offset, melody_match)
    words: list[dict[str, Any]] = []
    for word, (start, end), sim in zip(ref_words, frames, similarity, strict=True):
        begin_s = metrics.ref_frame_to_user_seconds(start, alignment.path, user.trim_start)
        end_s = metrics.ref_frame_to_user_seconds(
            max(end - 1, start), alignment.path, user.trim_start
        )
        words.append(
            {
                "text": word.text,
                "status": "scored",
                "similarity": _unit(sim),
                "start": begin_s,
                "end": max(end_s + HOP_S, begin_s),
            }
        )

    ref_points, user_points = metrics.contour_points(ref.f0_st, user_on_ref, _CONTOUR_STEP)
    contour = {
        "ref": ref_points,
        "user": user_points,
        "wordBounds": metrics.word_bounds(frames, _CONTOUR_STEP, length=len(ref_points)),
    }
    metrics_ms = _ms(started)

    started = time.perf_counter()
    texts = [word.text for word in ref_words]
    user_frames = prominence.user_word_frames(frames, alignment.path, int(user.f0_st.shape[0]))
    ref_prom = prominence.word_prominence(ref.f0_st, ref.energy_db, frames)
    user_prom = prominence.word_prominence(user.f0_st, user.energy_db, user_frames)
    stress = prominence.stress_entries(texts, ref_prom, user_prom)
    pauses = prominence.pause_entries(ref.energy_db, user.energy_db, frames, alignment.path)
    rule_issues = run_rules(
        RuleInput(
            ref=ref,
            user=user,
            alignment=alignment,
            words=texts,
            ref_word_frames=frames,
            user_word_frames=user_frames,
            user_st_on_ref=user_on_ref,
            pitch_range=pitch_range,
            ref_prominence=ref_prom,
            user_prominence=user_prom,
            word_issues_allowed=alignment.ok,
        )
    )
    issues = [rule_issue.issue for rule_issue in rule_issues]
    rules_ms = _ms(started)

    return ProsodyScore(
        speed=speed,
        pitch_range=pitch_range,
        melody_match=melody_match,
        intonation=intonation,
        rhythm=rhythm,
        overall=overall,
        words=words,
        contour=contour,
        stress=stress,
        pauses=pauses,
        issues=issues,
        rule_issues=rule_issues,
        word_texts=texts,
        alignment=alignment,
        word_issues_allowed=alignment.ok,
        ref_word_frames=frames,
        timing_ms={"align": align_ms, "metrics": metrics_ms, "rules": rules_ms},
    )


def to_score_result(
    score: ProsodyScore,
    *,
    lesson_id: str,
    segment_index: int,
    attempt: int,
    timing_ms: Mapping[str, float],
) -> ScoreResult:
    """Dựng và xác nhận `ScoreResult` từ điểm Lớp B (sound = null ở P2, D-04)."""
    payload: dict[str, Any] = {
        "lessonId": lesson_id,
        "segmentIndex": segment_index,
        "attempt": attempt,
        "mode": "full",
        "versions": {"scorer": SCORER_VERSION, "thresholds": THRESHOLDS_VERSION},
        "timingMs": {
            key: float(value) if math.isfinite(value) and value >= 0.0 else 0.0
            for key, value in timing_ms.items()
        },
        "scores": {
            "overall": score.overall,
            "sound": None,
            "intonation": score.intonation,
            "rhythm": score.rhythm,
        },
        "words": score.words,
        "prosody": {
            "speed": score.speed,
            "pitchRange": score.pitch_range,
            "melodyMatch": score.melody_match,
            "contour": score.contour,
            "stress": score.stress,
            "pauses": score.pauses,
        },
        "issues": score.issues,
        "tips": select_tips(
            score.rule_issues, score.word_texts, segment_index=segment_index, attempt=attempt
        ),
    }
    return ScoreResult.model_validate(payload)

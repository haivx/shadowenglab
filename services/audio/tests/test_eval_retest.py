"""Test-retest, kiểm tất định và đo điểm tổng của `make eval` (04-07, EVL-02, D-19, D-17).

Phần thuần (`evalkit.stats`) không cần DATA_DIR; phần đầu-cuối dựng bài tổng hợp như
`test_eval_analyze.py` rồi gọi `analyze.main([...])`.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from eval_synth import (
    DEFAULT_WORDS,
    LESSON_ID,
    case_dict,
    load_eval,
    load_evalkit,
    write_cases,
    write_clip,
    write_ready_lesson,
)
from synth import synth_sentence

from audio_service.config import get_settings


@pytest.fixture
def stats(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("stats", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


@pytest.fixture
def analyze(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("analyze", monkeypatch)


# --- hàm thuần (Task 1) ------------------------------------------------------------------------


def test_jaccard_of_two_empty_sets_is_one_and_of_disjoint_sets_is_zero(stats: ModuleType) -> None:
    assert stats.jaccard(set(), set()) == 1.0
    assert stats.jaccard({("FLAT_PITCH", None)}, set()) == 0.0
    assert stats.jaccard({("A", 1), ("B", None)}, {("A", 1)}) == pytest.approx(0.5)


def test_pooled_sd_pools_the_within_group_squared_deviations(stats: ModuleType) -> None:
    assert stats.pooled_sd([[1.0, 3.0], [5.0, 5.0]]) == pytest.approx(1.0)
    assert stats.pooled_sd([[2.0], [3.0]]) is None  # không nhóm nào có >= 2 giá trị


def test_sample_sd_uses_n_minus_one_and_is_zero_for_a_single_value(stats: ModuleType) -> None:
    assert stats.sample_sd([1.0, 3.0]) == pytest.approx(math.sqrt(2.0))
    assert stats.sample_sd([4.0]) == 0.0


def test_the_determinism_sample_is_five_and_icc_needs_five_groups(stats: ModuleType) -> None:
    assert stats.DETERMINISM_SAMPLE == 5
    assert stats.RETEST_MIN_GROUPS_FOR_ICC == 5


def _fake_clip(
    case_id: str,
    *,
    lesson: str = "L",
    segment: int = 0,
    kind: str = "error",
    error_type: str | None = "flat",
    word: int | None = None,
    overall: float = 0.5,
    issues: list[dict[str, Any]] | None = None,
    voiced: bool = True,
    stats: ModuleType,
) -> Any:
    case = SimpleNamespace(
        case_id=case_id,
        lesson_id=lesson,
        segment_index=segment,
        kind=kind,
        error_type=SimpleNamespace(root=error_type) if error_type is not None else None,
        word_index=word,
    )
    score = (
        SimpleNamespace(
            overall=overall,
            speed=overall,
            pitch_range=overall,
            melody_match=overall,
            issues=issues or [],
        )
        if voiced
        else None
    )
    return stats.ScoredClip(case, score)


def test_retest_groups_keep_only_keys_with_two_or_more_voiced_clips(stats: ModuleType) -> None:
    clips = [
        _fake_clip("c1", stats=stats),
        _fake_clip("c2", stats=stats),
        _fake_clip("c3", segment=1, stats=stats),  # nhóm khác (khác câu)
        _fake_clip("c4", error_type=None, kind="correct", stats=stats),  # nhóm khác (khác kind)
        _fake_clip("c5", segment=1, voiced=False, stats=stats),  # không tiếng: bị bỏ
    ]

    groups = stats.retest_groups(clips)

    assert list(groups) == [("L", 0, "error", "flat", None)]
    assert [item.case.case_id for item in groups[("L", 0, "error", "flat", None)]] == ["c1", "c2"]


def test_build_retest_reports_sd_and_the_mean_jaccard_of_issue_sets(stats: ModuleType) -> None:
    same = [{"code": "FLAT_PITCH", "wordIndex": None}]
    clips = [
        _fake_clip("c1", overall=0.50, issues=same, stats=stats),
        _fake_clip("c2", overall=0.60, issues=same, stats=stats),
    ]

    summary = stats.build_retest(clips)

    assert len(summary.groups) == 1
    group = summary.groups[0]
    assert group.k == 2
    assert group.sd["overall"] == pytest.approx(math.sqrt(0.005))
    assert group.jaccard == pytest.approx(1.0)
    assert summary.mean_jaccard == pytest.approx(1.0)
    assert summary.pooled["overall"] == pytest.approx(math.sqrt(0.005))
    assert summary.icc is None  # một nhóm: chưa đủ mẫu


# --- đầu-cuối (Task 1) -------------------------------------------------------------------------


def _audio(seed: int) -> Any:
    audio, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=seed)
    return audio


def _run(analyze: ModuleType, data_dir: Path, tmp_path: Path) -> int:
    return int(
        analyze.main(
            [
                "--cases",
                str(tmp_path / "cases.jsonl"),
                "--report",
                str(tmp_path / "report.md"),
                "--data-dir",
                str(data_dir),
            ]
        )
    )


def _section(report: str, heading: str) -> list[str]:
    lines = report.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {heading}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _write_two_flat_clips_and_a_correct_one(data_dir: Path, tmp_path: Path) -> None:
    lesson = write_ready_lesson(data_dir)
    first = write_clip(data_dir, LESSON_ID, 0, 1, _audio(1))
    second = write_clip(data_dir, LESSON_ID, 0, 2, _audio(2))
    other = write_clip(data_dir, LESSON_ID, 0, 3, _audio(3))
    flat = {"kind": "error", "error_type": "flat", "split": "tuning"}
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(lesson, 0, case_id="c0001", clip=first, **flat),
            case_dict(lesson, 0, case_id="c0002", clip=second, **flat),
            case_dict(lesson, 0, case_id="c0003", kind="correct", split="tuning", clip=other),
        ],
    )


def test_two_clips_of_one_group_give_a_retest_row_and_a_passing_determinism_line(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_two_flat_clips_and_a_correct_one(data_dir, tmp_path)

    code = _run(analyze, data_dir, tmp_path)

    assert code == 0, capsys.readouterr()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    section = _section(report, "Test-retest (D-19)")
    rows = [_cells(line) for line in section if line.startswith(f"| {LESSON_ID} |")]
    assert len(rows) == 1, section
    row = rows[0]
    assert row[1] == "0" and row[2] == "error" and row[3] == "flat" and row[4] == "2", row
    assert all(float(cell) >= 0.0 for cell in row[5:9]), row  # bốn SD
    assert 0.0 <= float(row[9]) <= 1.0, row
    text = "\n".join(section)
    assert "chưa đủ mẫu (1 nhóm)" in text
    assert "Tất định: PASS (3/3)" in text


def test_a_second_scoring_that_differs_marks_determinism_fail_with_the_case_id_and_exits_zero(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_two_flat_clips_and_a_correct_one(data_dir, tmp_path)
    rescore = load_evalkit("rescore", monkeypatch)
    real = rescore.score_clip
    calls: dict[str, int] = {}

    def flaky(clip: Any, **kwargs: Any) -> Any:
        score = real(clip, **kwargs)
        calls[clip.case.case_id] = calls.get(clip.case.case_id, 0) + 1
        if clip.case.case_id == "c0002" and calls["c0002"] >= 2 and score is not None:
            return dataclasses.replace(score, overall=score.overall + 0.01)
        return score

    monkeypatch.setattr(rescore, "score_clip", flaky)

    code = _run(analyze, data_dir, tmp_path)

    captured = capsys.readouterr()
    assert code == 0, captured  # chỉ tuning: không đổi exit code (04-01 J, D-21)
    assert "c0002" in captured.err and "tất định" in captured.err.lower()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    fail_lines = [line for line in report.splitlines() if line.startswith("Tất định: FAIL")]
    assert len(fail_lines) == 1 and "c0002" in fail_lines[0], fail_lines
    assert not any(line.startswith("Tất định: PASS") for line in report.splitlines())

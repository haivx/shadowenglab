"""Test-retest, kiểm tất định và đo điểm tổng của `make eval` (04-07, EVL-02, D-19, D-17).

Phần thuần (`evalkit.stats`) không cần DATA_DIR; phần đầu-cuối dựng bài tổng hợp như
`test_eval_analyze.py` rồi gọi `analyze.main([...])`.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import math
import re
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from eval_synth import (
    DEFAULT_WORDS,
    LESSON_ID,
    OTHER_WORDS,
    case_dict,
    load_eval,
    load_evalkit,
    write_cases,
    write_clip,
    write_ready_lesson,
)
from synth import synth_sentence

from audio_service.config import REPO_ROOT, get_settings


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


# --- ICC(1,1) và phân bố (Task 2) ---------------------------------------------------------------


def test_icc1_matches_the_three_reference_values(stats: ModuleType) -> None:
    assert stats.icc1([[1, 1], [2, 2], [3, 3]]) == pytest.approx(1.0)
    assert stats.icc1([[1, 2], [1, 2], [1, 2]]) == pytest.approx(-1.0)
    assert stats.icc1([[1, 3], [5, 7], [9, 11]]) == pytest.approx(0.88235, abs=1e-4)


def test_icc1_is_undefined_for_one_group_singleton_groups_or_a_zero_denominator(
    stats: ModuleType,
) -> None:
    assert stats.icc1([[1, 2]]) is None
    assert stats.icc1([[1], [2], [3]]) is None
    assert stats.icc1([[2, 2], [2, 2]]) is None


def test_distribution_is_n_median_and_the_quartiles(stats: ModuleType) -> None:
    assert stats.distribution([]) is None
    assert stats.distribution([0.5]) == (1, 0.5, 0.5, 0.5)
    assert stats.distribution([5.0, 1.0, 3.0, 2.0, 4.0]) == (5, 3.0, 2.0, 4.0)
    count, median, p25, p75 = stats.distribution([1.0, 2.0, 3.0, 4.0])
    assert (count, median) == (4, 2.5)
    assert p25 == pytest.approx(1.75) and p75 == pytest.approx(3.25)


def _five_groups(stats: ModuleType, count: int) -> list[Any]:
    clips = []
    for number in range(count):
        base = 0.2 + 0.15 * number
        for repeat, offset in enumerate((0.0, 0.01)):
            clips.append(
                _fake_clip(
                    f"c{number}{repeat}",
                    segment=number,
                    overall=base + offset,
                    stats=stats,
                )
            )
    return clips


def test_icc_is_computed_from_five_groups_and_left_out_below_that(stats: ModuleType) -> None:
    enough = stats.build_retest(_five_groups(stats, 5))
    too_few = stats.build_retest(_five_groups(stats, 4))

    assert len(enough.groups) == 5
    assert enough.icc is not None and enough.icc > 0.95
    assert len(too_few.groups) == 4 and too_few.icc is None


def test_cross_rows_give_the_median_and_the_share_of_pairs_that_align(stats: ModuleType) -> None:
    pairs = [
        stats.CrossPair("L", 0, 1, 0.30, True),
        stats.CrossPair("L", 1, 0, 0.50, False),
    ]

    rows = stats.cross_rows({"L": 2, "M": 1}, pairs)

    by_lesson = {row.lesson_id: row for row in rows}
    assert by_lesson["L"].n_pairs == 2
    assert by_lesson["L"].median == pytest.approx(0.40)
    assert by_lesson["L"].align_ok == 1
    assert by_lesson["M"].n_sentences == 1 and by_lesson["M"].n_pairs == 0
    assert by_lesson["M"].median is None


def _obs(source: str, lesson: str, overall: float, *, voiced: bool = True) -> Any:
    return SimpleNamespace(source=source, lesson_id=lesson, overall=overall, voiced=voiced)


def test_distribution_rows_cover_self_correct_and_error_per_lesson_and_skip_unvoiced(
    stats: ModuleType,
) -> None:
    observations = [
        _obs("self", "L", 0.99),
        _obs("self", "L", 0.97),
        _obs("error", "L", 0.60),
        _obs("error", "L", 0.0, voiced=False),  # không có tiếng: không có điểm để thống kê
    ]

    rows = stats.distribution_rows(observations)

    assert [(row.lesson_id, row.source) for row in rows] == [
        ("L", "self"),
        ("L", "correct"),
        ("L", "error"),
    ]
    assert rows[0].summary is not None and rows[0].summary[0] == 2
    assert rows[1].summary is None  # chưa có clip correct
    assert rows[2].summary is not None and rows[2].summary[0] == 1


def test_the_cross_risk_threshold_is_the_one_the_smoke_uses(stats: ModuleType) -> None:
    path = REPO_ROOT / "scripts" / "smoke_score.py"
    spec = importlib.util.spec_from_file_location("smoke_score_for_parity", path)
    assert spec is not None and spec.loader is not None
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)

    assert stats.CROSS_MEDIAN_RISK == smoke.CROSS_MEDIAN_MAX == 0.6


# --- render (Task 2) ------------------------------------------------------------------------------


def _render(monkeypatch: pytest.MonkeyPatch, **extra: Any) -> str:
    report = load_evalkit("report", monkeypatch)
    info = report.RunInfo(
        mode="tuning",
        thresholds_version="p2-1",
        scorer_version="prosody-2",
        feat_version="pf-2",
        git_sha="abc123",
        generated_at="2026-10-12T00:00:00Z",
        n_cases=0,
        n_scored=0,
        n_untagged=0,
    )
    return str(report.render_report(info, {}, enabled=(), **extra))


def test_a_cross_median_at_or_above_the_bar_is_labelled_a_d_a_risk(
    stats: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = stats.cross_rows(
        {"RISKY": 2, "SAFE": 2, "ALONE": 1},
        [
            stats.CrossPair("RISKY", 0, 1, 0.62, True),
            stats.CrossPair("RISKY", 1, 0, 0.64, True),
            stats.CrossPair("SAFE", 0, 1, 0.20, False),
            stats.CrossPair("SAFE", 1, 0, 0.30, False),
        ],
    )
    totals = stats.TotalsReport(cross=tuple(rows), distribution=())

    text = _render(monkeypatch, totals=totals)

    section = _section(text, "Điểm tổng (D-17, chỉ đo)")
    by_lesson = {_cells(line)[0]: line for line in section if line.startswith("| ")}
    assert "rủi ro D-a" in by_lesson["RISKY"]
    assert "rủi ro D-a" not in by_lesson["SAFE"]
    assert "cần ≥ 2 câu" in by_lesson["ALONE"]
    assert "công thức D-04 giữ nguyên" in "\n".join(section)


def test_an_empty_distribution_cell_is_a_dash_and_a_ready_icc_is_printed(
    stats: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = stats.distribution_rows([_obs("self", "L", 0.98)])
    totals = stats.TotalsReport(cross=(), distribution=tuple(rows))
    retest = stats.build_retest(_five_groups(stats, 5))

    text = _render(monkeypatch, totals=totals, retest=retest)

    section = _section(text, "Điểm tổng (D-17, chỉ đo)")
    cells = {_cells(line)[1]: _cells(line) for line in section if line.startswith("| L |")}
    assert cells["tự so"][2] == "1"
    assert cells["correct"][2:] == ["0", "—", "—", "—"]
    assert re.search(r"ICC\(1,1\) overall: 0\.\d{3} \(5 nhóm\)", text), text


# --- đầu-cuối (Task 2) ----------------------------------------------------------------------------


def _write_two_sentence_lesson(data_dir: Path, tmp_path: Path) -> None:
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])
    flat, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    spoken, _ = synth_sentence(OTHER_WORDS, seed=5)
    first = write_clip(data_dir, LESSON_ID, 0, 1, flat)
    second = write_clip(data_dir, LESSON_ID, 1, 1, spoken)
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(lesson, 0, case_id="c0001", kind="error", error_type="flat", clip=first),
            case_dict(lesson, 1, case_id="c0002", kind="correct", clip=second),
        ],
    )


def test_the_report_measures_the_overall_score_across_sentences_and_by_source(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_two_sentence_lesson(data_dir, tmp_path)

    code = _run(analyze, data_dir, tmp_path)

    assert code == 0, capsys.readouterr()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    section = _section(report, "Điểm tổng (D-17, chỉ đo)")
    cross = [_cells(line) for line in section if line.startswith(f"| {LESSON_ID} |")]
    pair_row = next(cells for cells in cross if cells[1] == "2")  # hai cặp chéo: 0->1 và 1->0
    assert 0.0 <= float(pair_row[2].split()[0]) <= 1.0, pair_row
    assert re.fullmatch(r"\d/2 \(\d+ %\)", pair_row[3]), pair_row
    rows = {cells[1]: cells for cells in cross if len(cells) >= 6}
    assert rows["tự so"][2] == "2"
    assert rows["correct"][2] == "1"
    assert rows["lỗi"][2] == "1"
    assert "công thức D-04 giữ nguyên" in "\n".join(section)


def test_a_lesson_with_one_sentence_in_the_set_says_it_needs_two_for_the_cross_pair(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _write_two_flat_clips_and_a_correct_one(data_dir, tmp_path)

    assert _run(analyze, data_dir, tmp_path) == 0

    section = _section((tmp_path / "report.md").read_text(encoding="utf-8"), "Điểm tổng (D-17")
    assert any("cần ≥ 2 câu" in line and line.startswith(f"| {LESSON_ID} |") for line in section)

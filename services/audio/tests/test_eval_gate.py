"""Cờ tắt rule đi tới report và gate của `make eval` (04-05, D-14, D-15, D-21, 04-01 F1-F3).

Phần đầu-cuối chạy `analyze.main` trên bài tổng hợp (cùng cách dựng với `test_eval_analyze.py`).
Phần thuần gọi thẳng `rule_status`, `pooled` và `verdict`, không đọc file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
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
from audio_service.rules import engine


@pytest.fixture
def analyze(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("analyze", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


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


def _row(report: str, rule: str) -> list[str]:
    for line in report.splitlines():
        if line.startswith(f"| {rule} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"không có dòng {rule} trong report:\n{report}")


def _flat_cases(data_dir: Path, tmp_path: Path) -> dict[str, Any]:
    lesson = write_ready_lesson(data_dir)
    audio, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, audio)
    case = case_dict(
        lesson, 0, case_id="c0001", kind="error", error_type="flat", split="tuning", clip=stem
    )
    write_cases(tmp_path / "cases.jsonl", [case])
    return lesson


# --- cờ D-15 đi tới report ---------------------------------------------------------------------


def test_a_disabled_flat_pitch_rule_is_marked_off_in_the_report_and_the_run_still_exits_zero(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _flat_cases(data_dir, tmp_path)
    monkeypatch.setattr(engine, "FLAT_PITCH_ENABLED", False)

    code = _run(analyze, data_dir, tmp_path)

    out = capsys.readouterr().out
    assert code == 0, out
    assert out.strip().splitlines()[-1].startswith("EVAL OK")
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "TẮT (D-15)" in _row(report, "FLAT_PITCH")
    assert "TẮT (D-15)" not in _row(report, "STRESS_MISMATCH")


def test_with_every_flag_on_no_rule_is_marked_off(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _flat_cases(data_dir, tmp_path)

    assert _run(analyze, data_dir, tmp_path) == 0

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "| TẮT (D-15)" not in report  # không ô bảng nào; chú giải có chữ TẮT thì được


# --- trạng thái D-14 và gate D-21: hàm thuần ----------------------------------------------------

ALL_CODES = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "PITCH_DEVIATION", "FLAT_PITCH")
OFF = "TẮT"
NOT_ENOUGH = "CHƯA ĐỦ MẪU"


@pytest.fixture
def counting(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("counting", monkeypatch)


@pytest.fixture
def report_mod(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("report", monkeypatch)


def test_the_gate_constants_are_the_values_liam_approved(counting: ModuleType) -> None:
    assert counting.PRECISION_BAR == 0.90
    assert counting.MIN_REPORTS == 5
    assert counting.TUNING_MARGIN == 0.95


@pytest.mark.parametrize(
    ("tp", "fp", "expected"),
    [
        (8, 2, "FAIL"),  # P 0.80 < 0.90
        (3, 0, NOT_ENOUGH),  # n < 5 và không FAIL
        (1, 1, "FAIL"),  # n >= 1 và P 0.50 < 0.90, dù n < 5
        (9, 1, "PASS"),  # n = 10, P 0.90
        (5, 0, "PASS"),  # n = 5 là đủ mẫu
        (4, 0, NOT_ENOUGH),  # n = 4
        (0, 0, NOT_ENOUGH),  # không báo lần nào
        (0, 1, "FAIL"),
        (89, 11, "FAIL"),  # P 0.89
    ],
)
def test_rule_status_follows_f2(counting: ModuleType, tp: int, fp: int, expected: str) -> None:
    assert counting.rule_status(counting.RuleTally(tp=tp, fp=fp), True) == expected


@pytest.mark.parametrize("tp", range(0, 5))
def test_fewer_than_five_reports_is_never_pass(counting: ModuleType, tp: int) -> None:
    assert counting.rule_status(counting.RuleTally(tp=tp, fp=0), True) != "PASS"


def test_a_disabled_rule_is_off_whatever_its_numbers_say(counting: ModuleType) -> None:
    for tally in (counting.RuleTally(tp=50, fp=0), counting.RuleTally(tp=0, fp=9)):
        assert counting.rule_status(tally, False) == OFF


def test_the_pooled_row_sums_only_the_enabled_rules(counting: ModuleType) -> None:
    tally = counting.RuleTally
    tallies = {
        "STRESS_MISMATCH": tally(tp=3, fp=1, expected=4, found=3),
        "FINAL_CONTOUR": tally(tp=10, fp=10, expected=10, found=10),
        "FLAT_PITCH": tally(tp=2, fp=0, expected=2, found=2),
    }

    got = counting.pooled(tallies, ("STRESS_MISMATCH", "FLAT_PITCH"))

    assert (got.tp, got.fp, got.expected, got.found) == (5, 1, 6, 5)
    empty = counting.pooled(tallies, ())
    assert (empty.tp, empty.fp, empty.expected, empty.found) == (0, 0, 0, 0)


def _self(counting: ModuleType, issues: int = 0, *, segment: int = 0) -> Any:
    codes = ("FLAT_PITCH",) * issues
    return counting.SelfRow("lessonA", segment, "heldout", True, 0.99, issues, codes)


def _by_split(counting: ModuleType, **heldout: Any) -> dict[str, dict[str, Any]]:
    """`heldout`: mã -> (tp, fp); mọi mã còn lại không báo lần nào."""
    tally = counting.RuleTally
    held = {}
    for code in ALL_CODES:
        tp, fp = heldout.get(code, (0, 0))
        held[code] = tally(tp=tp, fp=fp)
    return {"tuning": {code: tally() for code in ALL_CODES}, "heldout": held}


def test_verdict_fails_with_the_rule_code_when_an_enabled_rule_fails_on_heldout(
    analyze: ModuleType, counting: ModuleType
) -> None:
    by_split = _by_split(counting, FLAT_PITCH=(8, 2), STRESS_MISMATCH=(9, 1))

    message, code = analyze.verdict(by_split, [_self(counting)], ALL_CODES, holdout_included=True)

    assert code == 1
    assert message.startswith("EVAL FAILED: ")
    assert "FLAT_PITCH" in message
    assert "STRESS_MISMATCH" not in message  # PASS không phải lý do thất bại


def test_verdict_fails_when_the_self_compare_has_an_issue_and_names_the_sentence(
    analyze: ModuleType, counting: ModuleType
) -> None:
    rows = [_self(counting, 0), _self(counting, 2, segment=3)]

    message, code = analyze.verdict(_by_split(counting), rows, ALL_CODES, holdout_included=True)

    assert code == 1
    assert message.startswith("EVAL FAILED: ")
    assert "lessonA" in message and "3" in message


def test_verdict_joins_every_reason_with_a_semicolon(
    analyze: ModuleType, counting: ModuleType
) -> None:
    message, code = analyze.verdict(
        _by_split(counting, FLAT_PITCH=(0, 3), EXTRA_PAUSE=(1, 1)),
        [_self(counting, 1)],
        ALL_CODES,
        holdout_included=True,
    )

    assert code == 1
    reasons = message.removeprefix("EVAL FAILED: ").split("; ")
    assert len(reasons) == 3
    assert "FLAT_PITCH" in message and "EXTRA_PAUSE" in message and "lessonA" in message


def test_verdict_is_ok_when_every_rule_passes_lacks_samples_or_is_off_and_self_is_clean(
    analyze: ModuleType, counting: ModuleType
) -> None:
    by_split = _by_split(
        counting,
        STRESS_MISMATCH=(9, 1),  # PASS
        FINAL_CONTOUR=(3, 0),  # CHƯA ĐỦ MẪU
        PITCH_DEVIATION=(0, 7),  # đang tắt: số xấu không tính
    )
    enabled = ("STRESS_MISMATCH", "FINAL_CONTOUR", "EXTRA_PAUSE", "FLAT_PITCH")

    result = analyze.verdict(by_split, [_self(counting)], enabled, holdout_included=True)

    assert result == ("EVAL OK", 0)


def test_a_tuning_only_run_never_fails_but_warns_when_the_self_compare_has_an_issue(
    analyze: ModuleType, counting: ModuleType
) -> None:
    by_split = {"tuning": _by_split(counting)["tuning"]}
    by_split["tuning"]["FLAT_PITCH"] = counting.RuleTally(tp=0, fp=9)

    message, code = analyze.verdict(
        by_split, [_self(counting, 1)], ALL_CODES, holdout_included=False
    )

    assert code == 0
    assert message.startswith("EVAL OK")
    assert "tự so" in message and "lessonA" in message


def test_a_clean_tuning_only_run_reports_exactly_eval_ok(
    analyze: ModuleType, counting: ModuleType
) -> None:
    result = analyze.verdict(
        {"tuning": _by_split(counting)["tuning"]},
        [_self(counting)],
        ALL_CODES,
        holdout_included=False,
    )

    assert result == ("EVAL OK", 0)


# --- report: cột trạng thái, dòng gộp, dấu biên 95 %, dòng gate -----------------------------------


def _info(report_mod: ModuleType) -> Any:
    return report_mod.RunInfo(
        mode="tuning",
        thresholds_version="p2-1",
        scorer_version="prosody-2",
        feat_version="pf-2",
        git_sha="abc123",
        generated_at="2026-10-12T00:00:00Z",
        n_cases=3,
        n_scored=3,
        n_untagged=0,
    )


def _tallies(counting: ModuleType) -> dict[str, Any]:
    tally = counting.RuleTally
    result = {
        "STRESS_MISMATCH": tally(tp=3, fp=2, expected=5, found=3),
        "FINAL_CONTOUR": tally(tp=4, fp=0, expected=4, found=4),
        "EXTRA_PAUSE": tally(tp=1, fp=0, expected=2, found=1),
        "PITCH_DEVIATION": tally(),
        "FLAT_PITCH": tally(tp=19, fp=1, expected=20, found=19),
    }
    result[counting.POOLED] = counting.pooled(result, ALL_CODES)
    return result


def test_the_report_has_a_status_column_for_heldout_and_a_pooled_row_of_enabled_rules_only(
    counting: ModuleType, report_mod: ModuleType
) -> None:
    held = {
        "STRESS_MISMATCH": counting.RuleTally(tp=3, fp=0),
        "EXTRA_PAUSE": counting.RuleTally(tp=8, fp=2),
        "FLAT_PITCH": counting.RuleTally(tp=9, fp=1),
        "FINAL_CONTOUR": counting.RuleTally(tp=0, fp=5),
    }
    enabled = ("STRESS_MISMATCH", "EXTRA_PAUSE", "FLAT_PITCH")

    text = report_mod.render_report(
        _info(report_mod),
        _tallies(counting),
        enabled=enabled,
        heldout=held,
        gate_message="EVAL FAILED: EXTRA_PAUSE precision held-out 0.80 (n=10) < 0.90",
    )

    header = next(line for line in text.splitlines() if line.startswith("| Rule |"))
    assert "Trạng thái" in header
    assert _row(text, "STRESS_MISMATCH")[-1] == NOT_ENOUGH
    assert _row(text, "EXTRA_PAUSE")[-1] == "FAIL"
    assert _row(text, "FLAT_PITCH")[-1] == "PASS"
    assert _row(text, "FINAL_CONTOUR")[-1] == "TẮT (D-15)"
    assert _row(text, "PITCH_DEVIATION")[-1] == "TẮT (D-15)"
    pooled_cells = _row(text, counting.POOLED)
    assert pooled_cells[1] == "23" and pooled_cells[2] == "3"  # 3+1+19 TP, 2+0+1 FP; FINAL tắt
    assert pooled_cells[-1] == "FAIL"  # held-out gộp 20 TP, 3 FP -> P 0.87


def test_the_report_marks_the_tuning_rows_that_clear_the_95_percent_margin(
    counting: ModuleType, report_mod: ModuleType
) -> None:
    text = report_mod.render_report(_info(report_mod), _tallies(counting), enabled=ALL_CODES)

    assert "≥95 %" in _row(text, "FLAT_PITCH")[3]  # 19/20 = 0.95
    assert "≥95 %" in _row(text, "FINAL_CONTOUR")[3]  # 4/4
    assert "≥95 %" not in _row(text, "STRESS_MISMATCH")[3]  # 3/5
    assert "≥95 %" not in _row(text, "PITCH_DEVIATION")[3]  # n = 0 không có biên


def test_the_report_states_the_gate_or_that_it_does_not_apply(
    counting: ModuleType, report_mod: ModuleType
) -> None:
    tuning_only = report_mod.render_report(_info(report_mod), _tallies(counting), enabled=ALL_CODES)
    full = report_mod.render_report(
        _info(report_mod), _tallies(counting), enabled=ALL_CODES, gate_message="EVAL OK"
    )

    assert "gate: EVAL OK" in full
    start = tuning_only.index("## Tóm tắt theo rule")
    body = [line for line in tuning_only[start:].splitlines()[1:] if line.strip()]
    assert body[0] == "gate: không áp dụng (chỉ tuning)"


def test_without_heldout_numbers_the_status_column_is_a_dash_for_enabled_rules(
    counting: ModuleType, report_mod: ModuleType
) -> None:
    text = report_mod.render_report(_info(report_mod), _tallies(counting), enabled=ALL_CODES[:-1])

    assert _row(text, "STRESS_MISMATCH")[-1] == "—"
    assert _row(text, "FLAT_PITCH")[-1] == "TẮT (D-15)"

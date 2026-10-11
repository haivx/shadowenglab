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

    assert "TẮT" not in (tmp_path / "report.md").read_text(encoding="utf-8")

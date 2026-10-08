"""Phán quyết của scripts/smoke_jobs.py (hàm thuần; chạy API thật là `make smoke-jobs`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from audio_service.config import REPO_ROOT

Sample = tuple[float, str, str, float]


def _load_smoke_module() -> ModuleType:
    path = Path(REPO_ROOT) / "scripts" / "smoke_jobs.py"
    spec = importlib.util.spec_from_file_location("smoke_jobs_for_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _good_run() -> list[Sample]:
    return [
        (0.0, "queued", "queued", 0.01),
        (1.0, "downloading", "downloading", 0.01),
        (5.0, "queued", "queued", 0.02),
        (6.0, "separating", "queued", 0.02),
        (30.0, "ready", "queued", 0.02),
        (31.0, "ready", "separating", 0.02),
        (60.0, "ready", "ready", 0.02),
    ]


def test_good_run_has_no_problems() -> None:
    smoke = _load_smoke_module()

    assert smoke.check_timeline(_good_run()) == []


def test_serialised_downloads_are_reported() -> None:
    smoke = _load_smoke_module()
    samples: list[Sample] = [
        (0.0, "queued", "queued", 0.01),
        (1.0, "downloading", "queued", 0.01),
        (20.0, "ready", "queued", 0.01),
        (21.0, "ready", "downloading", 0.01),
        (40.0, "ready", "ready", 0.01),
    ]

    problems = smoke.check_timeline(samples)

    assert any("downloading" in problem for problem in problems)


def test_two_lessons_in_model_steps_at_once_are_reported() -> None:
    smoke = _load_smoke_module()
    samples = [*_good_run()[:4], (7.0, "transcribing", "separating", 0.02), _good_run()[-1]]

    problems = smoke.check_timeline(samples)

    assert any("bước model" in problem for problem in problems)


def test_slow_list_and_unfinished_lessons_are_reported() -> None:
    smoke = _load_smoke_module()
    samples: list[Sample] = [
        (0.0, "queued", "queued", 0.01),
        (1.0, "downloading", "downloading", 1.4),
        (2.0, "separating", "queued", 0.01),
    ]

    problems = smoke.check_timeline(samples)

    assert any("GET /lessons" in problem for problem in problems)
    assert any("trạng thái cuối" in problem for problem in problems)


def test_empty_timeline_is_a_problem() -> None:
    smoke = _load_smoke_module()

    assert smoke.check_timeline([]) != []


def test_format_timeline_prints_only_state_changes() -> None:
    smoke = _load_smoke_module()
    samples: list[Sample] = [
        (0.0, "queued", "queued", 0.01),
        (0.5, "queued", "queued", 0.05),
        (1.0, "downloading", "queued", 0.01),
    ]

    lines = smoke.format_timeline(samples).splitlines()

    assert len(lines) == 3  # tiêu đề + hai lần đổi trạng thái

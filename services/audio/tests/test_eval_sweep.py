"""Quét ngưỡng trên tuning (04-03, EVL-03/EVL-04, D-13, D-16).

Ba nhóm: ghi đè ngưỡng trong bộ nhớ (`evalkit.overrides`), quy tắc đề xuất (`sweep.propose`) và
`eval/sweep.py` đầu-cuối trên bài tổng hợp. Điều được chứng minh: ghi đè luôn được khôi phục, sweep
không ghi file nào (kể cả `thresholds.py`), không bao giờ đọc WAV held-out, và mỗi giá trị lưới ra
đúng một dòng.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from eval_synth import (
    DEFAULT_WORDS,
    LESSON_ID,
    case_dict,
    clip_stem,
    listing,
    load_eval,
    load_evalkit,
    write_cases,
    write_clip,
    write_ready_lesson,
)
from synth import synth_sentence

from audio_service import config
from audio_service.config import REPO_ROOT, get_settings

THRESHOLDS_PATH = (
    Path(REPO_ROOT) / "services" / "audio" / "src" / "audio_service" / "scoring" / "thresholds.py"
)


@pytest.fixture
def overrides(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("overrides", monkeypatch)


@pytest.fixture
def sweep(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("sweep", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


def _modules() -> tuple[ModuleType, ModuleType]:
    from audio_service.rules import engine
    from audio_service.scoring import thresholds

    return engine, thresholds


# --- ghi đè trong bộ nhớ (T-04-07) ---------------------------------------------------------------


def test_an_override_reaches_every_module_that_bound_the_name_and_is_restored_on_exit(
    overrides: ModuleType,
) -> None:
    engine, thresholds = _modules()
    before = (engine.FLAT_RATIO, thresholds.FLAT_RATIO)

    with overrides.override_thresholds(FLAT_RATIO=0.3):
        assert engine.FLAT_RATIO == 0.3
        assert thresholds.FLAT_RATIO == 0.3

    assert (engine.FLAT_RATIO, thresholds.FLAT_RATIO) == before


def test_an_exception_inside_the_block_still_restores_the_values(overrides: ModuleType) -> None:
    engine, thresholds = _modules()
    before = (engine.FLAT_RATIO, thresholds.FLAT_RATIO)

    with pytest.raises(RuntimeError, match="boom"):
        with overrides.override_thresholds(FLAT_RATIO=0.3):
            raise RuntimeError("boom")

    assert (engine.FLAT_RATIO, thresholds.FLAT_RATIO) == before


def test_a_name_that_is_not_a_threshold_raises_key_error_and_changes_nothing(
    overrides: ModuleType,
) -> None:
    engine, thresholds = _modules()
    before = (engine.FLAT_RATIO, thresholds.FLAT_RATIO)

    with pytest.raises(KeyError):
        with overrides.override_thresholds(FLAT_RATIO=0.3, NOT_A_THRESHOLD=1.0):
            raise AssertionError("không được vào khối")

    assert (engine.FLAT_RATIO, thresholds.FLAT_RATIO) == before


def test_bound_in_names_the_modules_that_bind_a_name(overrides: ModuleType) -> None:
    assert overrides.bound_in("FLAT_RATIO") == [
        "audio_service.scoring.thresholds",
        "audio_service.rules.engine",
    ]
    assert "audio_service.scoring.metrics" in overrides.bound_in("PAUSE_USER_MS")
    assert overrides.bound_in("ALIGN_COST_MAX") == [
        "audio_service.scoring.thresholds",
        "audio_service.scoring.align",
    ]


def test_every_module_that_imports_threshold_constants_is_a_consumer(
    overrides: ModuleType,
) -> None:
    """Thêm một module import hằng ngưỡng mà quên CONSUMER_MODULES thì sweep đo sai âm thầm."""
    package = Path(config.__file__).parent
    versions = {"THRESHOLDS_VERSION", "SCORER_VERSION"}
    importers: set[str] = set()
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ImportFrom) and node.module is not None):
                continue
            if node.module != "audio_service.scoring.thresholds":
                continue
            if {alias.name for alias in node.names} <= versions:
                continue
            relative = path.relative_to(package.parent).with_suffix("")
            importers.add(".".join(relative.parts))
    assert importers, "không tìm thấy module nào import hằng ngưỡng"
    assert importers <= set(overrides.CONSUMER_MODULES), importers - set(overrides.CONSUMER_MODULES)


# --- quy tắc đề xuất (D-13) ----------------------------------------------------------------------


def _row(sweep: ModuleType, value: float, precision: float | None, found: int) -> Any:
    n = 100 if precision is not None else 0
    tp = round(precision * n) if precision is not None else 0
    return sweep.SweepRow(
        value=value,
        tp=tp,
        fp=n - tp,
        precision=precision,
        ci=None,
        found=found,
        expected=10,
        align_fail_rate=None,
    )


def test_propose_takes_the_highest_recall_among_values_that_reach_the_precision_floor(
    sweep: ModuleType,
) -> None:
    rows = [
        _row(sweep, 0.5, 1.0, 5),
        _row(sweep, 0.6, 0.96, 8),
        _row(sweep, 0.7, 0.90, 10),  # recall cao nhất nhưng P dưới 0.95
    ]
    assert sweep.propose(rows, current=0.6) == 0.6
    assert sweep.propose(rows, current=0.5) == 0.6  # không phải "gần hiện tại" mà là recall


def test_propose_returns_none_when_no_value_reaches_the_precision_floor(sweep: ModuleType) -> None:
    rows = [_row(sweep, 0.5, 0.94, 9), _row(sweep, 0.6, None, 0), _row(sweep, 0.7, 0.5, 10)]
    assert sweep.propose(rows, current=0.6) is None


def test_propose_breaks_a_recall_tie_by_distance_to_the_current_value(sweep: ModuleType) -> None:
    rows = [_row(sweep, 0.4, 1.0, 8), _row(sweep, 0.5, 1.0, 8), _row(sweep, 0.9, 1.0, 8)]
    assert sweep.propose(rows, current=0.55) == 0.5
    assert sweep.propose(rows, current=0.85) == 0.9


def test_propose_floor_is_inclusive_and_configurable(sweep: ModuleType) -> None:
    rows = [_row(sweep, 0.5, 0.95, 4), _row(sweep, 0.6, 0.90, 9)]
    assert sweep.propose(rows, current=0.6) == 0.5
    assert sweep.propose(rows, current=0.6, min_precision=0.90) == 0.6


# --- đầu-cuối trên bài tổng hợp (tracer: FLAT_RATIO) ---------------------------------------------


def _flat_audio() -> Any:
    audio, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    return audio


def _natural_audio() -> Any:
    audio, _ = synth_sentence(DEFAULT_WORDS, seed=4)
    return audio


def _argv(data_dir: Path, tmp_path: Path, *params: str) -> list[str]:
    argv = ["--cases", str(tmp_path / "cases.jsonl"), "--data-dir", str(data_dir)]
    for param in params:
        argv += ["--param", param]
    return argv


def _write_tracer_cases(data_dir: Path, tmp_path: Path) -> str:
    """Flat tuning + correct tuning + một case held-out có clip không tồn tại; trả stem ma."""
    lesson = write_ready_lesson(data_dir)
    flat = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    correct = write_clip(data_dir, LESSON_ID, 0, 2, _natural_audio())
    ghost = clip_stem(LESSON_ID, 0, 3)  # WAV không tồn tại: held-out không được đọc
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(lesson, 0, case_id="c0001", kind="error", error_type="flat", clip=flat),
            case_dict(lesson, 0, case_id="c0002", kind="correct", clip=correct),
            case_dict(
                lesson,
                0,
                case_id="c0003",
                kind="error",
                error_type="flat",
                split="heldout",
                clip=ghost,
            ),
        ],
    )
    return ghost


def _value_rows(stdout: str, grid: tuple[float, ...]) -> list[str]:
    """Các dòng bảng có ô đầu là một giá trị lưới (kể cả có dấu `*`)."""
    rows = []
    for line in stdout.splitlines():
        if not line.startswith("|"):
            continue
        first = line.strip().strip("|").split("|")[0].strip().rstrip("*").strip()
        try:
            value = float(first)
        except ValueError:
            continue
        if value in grid:
            rows.append(line)
    return rows


def test_one_parameter_is_swept_end_to_end_with_a_proposal_and_no_file_touched(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ghost = _write_tracer_cases(data_dir, tmp_path)
    thresholds_before = hashlib.sha256(THRESHOLDS_PATH.read_bytes()).hexdigest()
    data_before = listing(data_dir)
    engine, _ = _modules()
    ratio_before = engine.FLAT_RATIO

    code = sweep.main(_argv(data_dir, tmp_path, "FLAT_RATIO"))

    out = capsys.readouterr().out
    assert code == 0, out
    grid = sweep.SWEEP_GRID["FLAT_RATIO"][1]
    rows = _value_rows(out, grid)
    assert len(rows) == len(grid), out
    marked = [row for row in rows if "*" in row.split("|")[1]]
    assert [row.split("|")[1].strip() for row in marked] == [f"{ratio_before:g}*"]
    proposals = [line for line in out.splitlines() if line.startswith("Đề xuất FLAT_RATIO")]
    assert len(proposals) == 1, out
    assert ghost not in out
    assert hashlib.sha256(THRESHOLDS_PATH.read_bytes()).hexdigest() == thresholds_before
    assert listing(data_dir) == data_before
    assert engine.FLAT_RATIO == ratio_before, "ghi đè phải được khôi phục sau khi sweep xong"


def test_a_missing_split_exits_two_and_never_scores_anything(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lesson = write_ready_lesson(data_dir)
    write_cases(
        tmp_path / "cases.jsonl",
        [case_dict(lesson, 0, case_id="c0001", kind="error", error_type="flat", split=None)],
    )

    code = sweep.main(_argv(data_dir, tmp_path, "FLAT_RATIO"))

    captured = capsys.readouterr()
    assert code == 2
    assert "D-12" in captured.err
    assert "Đề xuất" not in captured.out


# --- lưới đủ 04-01 mục G, căn, ghi chú dùng chung, nhớ đệm (Task 2) --------------------------

EXPECTED_GRID: dict[str, tuple[str, tuple[float, ...]]] = {
    "STRESS_MARGIN_Z": ("STRESS_MISMATCH", (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2)),
    "PAUSE_USER_MS": ("EXTRA_PAUSE", (150, 200, 250, 300, 350, 400)),
    "PAUSE_REF_MS": ("EXTRA_PAUSE", (60, 80, 100, 120, 150)),
    "FINAL_SLOPE_MIN_ST_S": ("FINAL_CONTOUR", (3, 4, 5, 6, 7, 8, 10)),
    "FLAT_RATIO": ("FLAT_PITCH", (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)),
    "FLAT_REF_MIN_STD_ST": ("FLAT_PITCH", (1.0, 1.5, 2.0, 2.5, 3.0)),
    "PITCH_DEVIATION_ST": ("PITCH_DEVIATION", (2.0, 2.5, 3.0, 3.5, 4.0, 5.0)),
    "PD_SIGN_CONSISTENCY": ("PITCH_DEVIATION", (0.6, 0.7, 0.8, 0.9)),
    "ALIGN_COST_MAX": ("WORD_RULES", (0.90, 1.00, 1.10, 1.20, 1.30)),
}


def test_the_grid_is_exactly_the_one_liam_approved_and_every_key_is_a_threshold(
    sweep: ModuleType,
) -> None:
    from audio_service.scoring import thresholds

    assert dict(sweep.SWEEP_GRID) == EXPECTED_GRID
    for name in sweep.SWEEP_GRID:
        assert hasattr(thresholds, name), name


def test_the_pooled_word_rules_row_adds_the_three_word_level_rules(
    sweep: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    counting = load_evalkit("counting", monkeypatch)
    tallies = {
        "STRESS_MISMATCH": counting.RuleTally(tp=3, fp=1, expected=4, found=3),
        "EXTRA_PAUSE": counting.RuleTally(tp=2, fp=0, expected=3, found=2),
        "PITCH_DEVIATION": counting.RuleTally(tp=1, fp=1, expected=2, found=1),
        "FLAT_PITCH": counting.RuleTally(tp=9, fp=9, expected=9, found=9),  # không được tính
    }

    row = sweep.make_row(1.1, tallies, "WORD_RULES", 0.25)

    assert (row.tp, row.fp, row.found, row.expected) == (6, 2, 6, 9)
    assert row.precision == pytest.approx(6 / 8)
    assert row.align_fail_rate == 0.25
    assert row.ci is not None and row.ci[0] < 0.75 < row.ci[1]


def _headers(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if line.startswith("## ")]


def test_a_parameter_shared_with_the_overall_score_says_so_in_its_header(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_tracer_cases(data_dir, tmp_path)

    code = sweep.main(_argv(data_dir, tmp_path, "PAUSE_USER_MS", "PAUSE_REF_MS", "FLAT_RATIO"))

    out = capsys.readouterr().out
    assert code == 0, out
    user, ref, flat = _headers(out)[:3]
    assert user.startswith("## PAUSE_USER_MS (rule EXTRA_PAUSE; hiện tại 250)")
    assert "cũng đổi metrics.speed (điểm tổng)" in user
    assert "prominence" in ref  # PAUSE_REF_MS cũng vào prominence.pause_entries
    assert " — " not in flat, "FLAT_RATIO chỉ có engine và thresholds nên không có ghi chú"


def test_the_alignment_threshold_reports_the_alignment_failure_rate_and_pooled_word_rules(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_tracer_cases(data_dir, tmp_path)

    code = sweep.main(_argv(data_dir, tmp_path, "ALIGN_COST_MAX"))

    out = capsys.readouterr().out
    assert code == 0, out
    header = _headers(out)[0]
    assert "STRESS_MISMATCH" in header and "EXTRA_PAUSE" in header and "PITCH_DEVIATION" in header
    assert "đổi alignment.ok cho mọi rule theo từ" in header
    table_header = next(line for line in out.splitlines() if line.startswith("| Giá trị"))
    assert "Căn thất bại" in table_header
    rows = _value_rows(out, sweep.SWEEP_GRID["ALIGN_COST_MAX"][1])
    assert len(rows) == 5
    for row in rows:
        rate = row.strip().strip("|").split("|")[-1].strip()
        assert rate == "—" or rate.endswith(" %"), row


def test_an_unknown_parameter_exits_two_naming_it(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_tracer_cases(data_dir, tmp_path)

    code = sweep.main(_argv(data_dir, tmp_path, "FLAT_RATIO", "NOPE"))

    captured = capsys.readouterr()
    assert code == 2
    assert "NOPE" in captured.err
    assert "Đề xuất" not in captured.out


def test_without_param_every_grid_entry_is_swept_and_summarised_in_grid_order(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_tracer_cases(data_dir, tmp_path)
    # Lưới rút gọn (2 giá trị) để chạy nhanh; thứ tự và mã rule giữ nguyên.
    monkeypatch.setattr(
        sweep,
        "SWEEP_GRID",
        {name: (code, grid[:2]) for name, (code, grid) in EXPECTED_GRID.items()},
    )

    code = sweep.main(_argv(data_dir, tmp_path))

    out = capsys.readouterr().out
    assert code == 0, out
    swept = [header.split()[1] for header in _headers(out) if "(rule" in header]
    assert swept == list(EXPECTED_GRID)
    lines = out.splitlines()
    start = lines.index("## Tóm tắt đề xuất")
    summary = [line for line in lines[start + 1 :] if line.startswith("- ")]
    assert [line.split(":")[0].removeprefix("- ") for line in summary] == list(EXPECTED_GRID)


def test_features_are_computed_once_per_input_and_alignment_only_reruns_for_align_params(
    sweep: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from audio_service.scoring import align as align_module

    rescore = load_evalkit("rescore", monkeypatch)
    _write_tracer_cases(data_dir, tmp_path)  # 2 clip tuning + 1 câu tự so; held-out không đếm
    features: list[int] = []
    aligned: list[int] = []
    real_prepare = rescore.prepare_features
    real_align = align_module.align

    def counting_prepare(mono: Any) -> Any:
        features.append(1)
        return real_prepare(mono)

    def counting_align(ref_mfcc: Any, user_mfcc: Any) -> Any:
        aligned.append(1)
        return real_align(ref_mfcc, user_mfcc)

    monkeypatch.setattr(rescore, "prepare_features", counting_prepare)
    monkeypatch.setattr(align_module, "align", counting_align)

    assert sweep.main(_argv(data_dir, tmp_path, "FLAT_RATIO", "PAUSE_USER_MS")) == 0
    assert len(features) == 3, "feature tính một lần mỗi clip và mỗi câu tự so, không mỗi giá trị"
    assert len(aligned) == 3, "căn một lần mỗi đầu vào rồi nhớ đệm khi tham số không phải ALIGN_*"

    aligned.clear()
    grid = sweep.SWEEP_GRID["ALIGN_COST_MAX"][1]
    assert sweep.main(_argv(data_dir, tmp_path, "ALIGN_COST_MAX")) == 0
    assert len(aligned) == 3 * len(grid), "tham số ALIGN_* phải căn lại ở từng giá trị"

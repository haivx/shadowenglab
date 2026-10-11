"""`make eval` đầu-cuối trên bài tổng hợp (04-02, EVL-02): cases.jsonl -> chấm lại -> report.md.

`eval/analyze.py` không nằm trong package của service nên được nạp bằng `eval_synth.load_eval`.
Mỗi test dựng một DATA_DIR tạm có bài `ready` tổng hợp, clip eval và `cases.jsonl`, rồi gọi
`analyze.main([...])`. Hai điều được chứng minh ở đây: các lối thoát 2 (dữ liệu sai, D-05, D-12) và
script CHỈ ĐỌC DATA_DIR (T-04-04); held-out không bao giờ được nạp (D-16).
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from eval_synth import (
    DEFAULT_WORDS,
    LESSON_ID,
    OTHER_WORDS,
    case_dict,
    clip_stem,
    listing,
    load_eval,
    write_cases,
    write_clip,
    write_ready_lesson,
)
from synth import synth_sentence

from audio_service.config import get_settings
from audio_service.lesson import pipeline
from audio_service.scoring.features import FEAT_VERSION
from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION


@pytest.fixture
def analyze(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("analyze", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    # setenv trước để monkeypatch khôi phục cả những gì main() tự đặt.
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


def _flat_audio() -> Any:
    audio, _ = synth_sentence(DEFAULT_WORDS, flat_f0=180.0, seed=4)
    return audio


def _run(analyze: ModuleType, data_dir: Path, tmp_path: Path, cases: Path | None = None) -> int:
    return int(
        analyze.main(
            [
                "--cases",
                str(cases if cases is not None else tmp_path / "cases.jsonl"),
                "--report",
                str(tmp_path / "report.md"),
                "--data-dir",
                str(data_dir),
            ]
        )
    )


def _row(report: str, rule: str) -> list[str]:
    """Các ô của dòng bảng bắt đầu bằng `| <rule> |` (đã strip)."""
    for line in report.splitlines():
        if line.startswith(f"| {rule} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"không có dòng {rule} trong report:\n{report}")


def _leftover_temp_dirs() -> set[str]:
    return {p.name for p in Path(tempfile.gettempdir()).glob("shadowenglab-eval-*")}


def _flat_case(lesson: dict[str, Any], stem: str | None, **overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "case_id": "c0001",
        "kind": "error",
        "error_type": "flat",
        "split": "tuning",
        "clip": stem,
    }
    kwargs.update(overrides)
    return case_dict(lesson, 0, **kwargs)


# --- đường chính -------------------------------------------------------------------------------


def test_one_flat_case_is_scored_end_to_end_and_reported_as_a_true_positive(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, stem)])

    code = _run(analyze, data_dir, tmp_path)

    out = capsys.readouterr().out
    assert code == 0, out
    assert out.strip().splitlines()[-1] == "EVAL OK"
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    head = "\n".join(report.splitlines()[:12])
    for version in (THRESHOLDS_VERSION, SCORER_VERSION, FEAT_VERSION):
        assert version in head
    row = _row(report, "FLAT_PITCH")
    assert row[1] == "1" and row[2] == "0", row  # TP 1, FP 0
    assert "1/1" in row[4], row  # recall 1/1
    assert str(tmp_path) not in report and "/Users/" not in report  # không đường dẫn tuyệt đối


def test_a_data_dir_is_left_exactly_as_it_was_and_no_temp_dir_remains(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, stem)])
    before = listing(data_dir)
    temp_before = _leftover_temp_dirs()

    assert _run(analyze, data_dir, tmp_path) == 0

    assert listing(data_dir) == before, "analyze chỉ được đọc DATA_DIR (T-04-04)"
    assert not (data_dir / "app.db").exists()
    assert _leftover_temp_dirs() == temp_before, "thư mục tạm phải bị xoá trong finally"


# --- lối thoát 2 -------------------------------------------------------------------------------


def test_a_missing_cases_file_exits_two_and_names_the_file(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = _run(analyze, data_dir, tmp_path)

    assert code == 2
    assert "cases.jsonl" in capsys.readouterr().err
    assert not (tmp_path / "report.md").exists()


def test_a_case_without_split_exits_two_citing_d12_and_writes_no_report(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, None, split=None)])

    code = _run(analyze, data_dir, tmp_path)

    assert code == 2
    assert "D-12" in capsys.readouterr().err
    assert not (tmp_path / "report.md").exists()


def test_a_sentence_stamp_mismatch_exits_two_with_the_case_id_and_keeps_the_old_report(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    bad = _flat_case(lesson, stem)
    bad["segTextHash"] = "0" * 16
    write_cases(tmp_path / "cases.jsonl", [bad])
    (tmp_path / "report.md").write_bytes(b"bao cao cu\n")

    code = _run(analyze, data_dir, tmp_path)

    err = capsys.readouterr().err
    assert code == 2
    assert "c0001" in err and "D-05" in err
    assert (tmp_path / "report.md").read_bytes() == b"bao cao cu\n"


def test_a_lesson_that_does_not_exist_exits_two_with_the_case_id(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, None)])
    # Xoá bài sau khi viết case: giống Liam xoá bài trong thư viện.
    (data_dir / "lessons" / LESSON_ID / "lesson.json").unlink()

    code = _run(analyze, data_dir, tmp_path)

    err = capsys.readouterr().err
    assert code == 2
    assert "c0001" in err and "D-05" in err


def test_a_tuning_clip_whose_wav_is_missing_exits_two_naming_the_stem(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = clip_stem(LESSON_ID, 0, 1)  # không ghi WAV
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, stem)])

    code = _run(analyze, data_dir, tmp_path)

    err = capsys.readouterr().err
    assert code == 2
    assert stem in err
    assert not (tmp_path / "report.md").exists()


def test_a_clip_name_that_would_escape_the_clips_folder_exits_two(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T-04-03: `case.clip` đi vào đường dẫn file nên phải qua CLIP_STEM_RE."""
    lesson = write_ready_lesson(data_dir)
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, "../../etc/passwd")])

    code = _run(analyze, data_dir, tmp_path)

    assert code == 2
    assert "c0001" in capsys.readouterr().err


def test_a_sidecar_that_names_another_sentence_exits_two(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    sidecar = data_dir / "eval_clips" / f"{stem}.json"
    sidecar.write_text(
        sidecar.read_text(encoding="utf-8").replace('"segmentIndex": 0', '"segmentIndex": 3')
    )
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, stem)])

    code = _run(analyze, data_dir, tmp_path)

    assert code == 2
    assert stem in capsys.readouterr().err


# --- held-out không được nạp (D-16) ------------------------------------------------------------


def test_a_heldout_case_is_never_loaded_even_when_its_clip_does_not_exist(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    ghost = clip_stem(LESSON_ID, 0, 2)  # WAV không tồn tại
    write_cases(
        tmp_path / "cases.jsonl",
        [
            _flat_case(lesson, stem),
            _flat_case(lesson, ghost, case_id="c0002", split="heldout"),
        ],
    )

    code = _run(analyze, data_dir, tmp_path)

    out = capsys.readouterr().out
    assert code == 0, out
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "khoá (D-16)" in report
    assert ghost not in report


# --- các mục của report (Task 2) ---------------------------------------------------------------


def test_the_report_lists_false_positives_alignment_failure_rates_and_coverage(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lesson = write_ready_lesson(data_dir)
    flat_stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    correct_stem = write_clip(data_dir, LESSON_ID, 0, 2, _flat_audio())
    write_cases(
        tmp_path / "cases.jsonl",
        [
            _flat_case(lesson, flat_stem),
            # Một clip "đúng" mà scorer vẫn báo FLAT_PITCH: một FP để Liam nghe lại (D-09, D-18b).
            _flat_case(lesson, correct_stem, case_id="c0002", kind="correct", error_type=None),
            _flat_case(lesson, None, case_id="c0003", split="heldout"),
        ],
    )

    code = _run(analyze, data_dir, tmp_path)

    out = capsys.readouterr().out
    assert code == 0, out
    assert "FP 1" in out
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    for heading in ("## Danh sách FP", "## Tỉ lệ căn thất bại (D-11b)", "## Phủ"):
        assert heading in report
    fp_lines = [line for line in report.splitlines() if line.startswith("|") and "c0002" in line]
    assert any("FLAT_PITCH" in line and correct_stem in line for line in fp_lines), fp_lines
    assert any(
        line.startswith(f"| {LESSON_ID} | flat |") and "0/1" in line for line in report.splitlines()
    )
    assert "| flat | heldout | 1 | 0 | 0 |" in report
    assert "| flat | tuning | 1 | 1 | 1 |" in report


# --- mốc tự so (Task 3, D-18a) -------------------------------------------------------------------


def _section(report: str, heading: str) -> list[str]:
    """Các dòng của mục `## <heading>` cho tới mục kế tiếp."""
    lines = report.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {heading}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def _self_rows(report: str) -> list[list[str]]:
    rows = []
    for line in _section(report, "Mốc tự so (D-18a)"):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith(f"| {LESSON_ID} |"):
            rows.append(cells)
    return rows


def test_every_tuning_sentence_gets_a_self_compare_row_that_is_clean(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    write_cases(
        tmp_path / "cases.jsonl",
        [
            _flat_case(lesson, stem),
            # Câu 1 chỉ có một case chưa gắn clip: vẫn có mốc tự so (mọi câu có case trong tập).
            case_dict(lesson, 1, case_id="c0002", kind="correct"),
        ],
    )

    code = _run(analyze, data_dir, tmp_path)

    assert code == 0, capsys.readouterr()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    rows = _self_rows(report)
    assert [row[1] for row in rows] == ["0", "1"], rows
    for row in rows:
        assert row[2] == "tuning"
        assert float(row[3]) >= 0.9, row
        assert row[4] == "0", row  # không issue nào trên mốc tự so
    assert "tự so: 2 câu" in "\n".join(_section(report, "Mốc tự so (D-18a)"))


def test_a_sentence_that_only_has_a_heldout_case_gets_no_self_compare_in_a_tuning_run(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])
    stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio())
    write_cases(
        tmp_path / "cases.jsonl",
        [
            _flat_case(lesson, stem),
            case_dict(lesson, 1, case_id="c0002", kind="correct", split="heldout"),
        ],
    )

    assert _run(analyze, data_dir, tmp_path) == 0

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert [row[1] for row in _self_rows(report)] == ["0"]


def test_missing_vocal_stem_stops_the_self_compare_with_exit_two(
    analyze: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson = write_ready_lesson(data_dir)
    for stem_file in data_dir.rglob("vocals.wav"):
        stem_file.unlink()
    write_cases(tmp_path / "cases.jsonl", [_flat_case(lesson, None)])

    code = _run(analyze, data_dir, tmp_path)

    assert code == 2
    assert pipeline.STEMS_MISSING_MESSAGE in capsys.readouterr().err
    assert not (tmp_path / "report.md").exists()

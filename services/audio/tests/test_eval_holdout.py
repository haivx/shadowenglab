"""Khoá held-out của `make eval` (04-06, EVL-03, D-09, D-12, D-16, D-21).

Phần đầu-cuối chạy `analyze.main` trên bài tổng hợp (cùng cách dựng với `test_eval_analyze.py`):
mặc định không đọc WAV held-out và không chạm file log; `--holdout` chấm cả hai tập, ghi đúng một
dòng log mỗi lần mở và áp gate D-21. Phần thuần gọi thẳng `evalkit.holdout` (digest, log, đóng
băng).
"""

from __future__ import annotations

import json
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

from audio_service.config import REPO_ROOT, get_settings
from audio_service.contracts_gen import EvalAlsoPresent, EvalCase

LOG_KEYS = {
    "openedAt",
    "thresholdsVersion",
    "scorerVersion",
    "featVersion",
    "gitSha",
    "splits",
    "digests",
}


@pytest.fixture
def analyze(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("analyze", monkeypatch)


@pytest.fixture
def tag_clips(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("tag_clips", monkeypatch)


@pytest.fixture
def holdout(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("holdout", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


def _flat(words: Any, seed: int = 4) -> Any:
    audio, _ = synth_sentence(list(words), flat_f0=180.0, seed=seed)
    return audio


def _natural_ref(words: Any, seed: int) -> Any:
    """Đúng tín hiệu `write_ready_lesson` dùng làm bản gốc của câu số `seed - 1`."""
    audio, _ = synth_sentence(list(words), seed=seed)
    return audio


def _run(analyze: ModuleType, data_dir: Path, tmp_path: Path, *extra: str) -> int:
    return int(
        analyze.main(
            [
                "--cases",
                str(tmp_path / "cases.jsonl"),
                "--report",
                str(tmp_path / "report.md"),
                "--data-dir",
                str(data_dir),
                "--holdout-log",
                str(tmp_path / "holdout_log.jsonl"),
                *extra,
            ]
        )
    )


def _log(tmp_path: Path) -> list[dict[str, Any]]:
    path = tmp_path / "holdout_log.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def _row(report: str, rule: str) -> list[str]:
    for line in report.splitlines():
        if line.startswith(f"| {rule} |"):
            return [cell.strip() for cell in line.strip().strip("|").split("|")]
    raise AssertionError(f"không có dòng {rule} trong report:\n{report}")


def _two_sentence_cases(
    data_dir: Path, tmp_path: Path, *, heldout_audio: Any | None
) -> dict[str, Any]:
    """Câu 0: case lỗi `flat` (tuning, clip phẳng). Câu 1: case `correct` held-out; clip là
    `heldout_audio` (None = trỏ tới WAV không tồn tại)."""
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS])
    tuning_stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat(DEFAULT_WORDS))
    if heldout_audio is None:
        held_stem = f"{LESSON_ID}_0001_01"  # không có WAV nào
    else:
        held_stem = write_clip(data_dir, LESSON_ID, 1, 1, heldout_audio)
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(
                lesson, 0, case_id="c0001", kind="error", error_type="flat", clip=tuning_stem
            ),
            case_dict(lesson, 1, case_id="c0002", kind="correct", split="heldout", clip=held_stem),
        ],
    )
    return lesson


# --- không --holdout: held-out khoá ------------------------------------------------------------


def test_without_the_holdout_flag_heldout_wavs_are_never_read_and_no_log_is_created(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=None)

    code = _run(analyze, data_dir, tmp_path)

    assert code == 0
    assert not (tmp_path / "holdout_log.jsonl").exists()
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "khoá (D-16)" in report


# --- --holdout: chấm held-out, ghi log, áp gate D-21 -------------------------------------------


def test_holdout_run_with_a_failing_rule_exits_one_and_appends_one_seven_key_log_line(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=_flat(DEFAULT_WORDS))

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    out = capsys.readouterr().out
    assert code == 1, out
    last = out.strip().splitlines()[-1]
    assert last.startswith("EVAL FAILED: ") and "FLAT_PITCH" in last
    entries = _log(tmp_path)
    assert len(entries) == 1
    assert set(entries[0]) == LOG_KEYS
    assert set(entries[0]["digests"]) == {"c0002"}, "digests chỉ có case held-out"
    assert entries[0]["splits"] == {"c0001": "tuning", "c0002": "heldout"}
    assert entries[0]["openedAt"].endswith("Z")


def test_a_clean_holdout_run_exits_zero_and_adds_a_second_log_line_listed_in_the_report(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=_flat(DEFAULT_WORDS))
    assert _run(analyze, data_dir, tmp_path, "--holdout") == 1

    # Cùng nhãn, clip held-out đổi thành đúng tín hiệu bản gốc: sạch (digest không phụ thuộc WAV).
    write_clip(data_dir, LESSON_ID, 1, 1, _natural_ref(DEFAULT_WORDS, seed=2))
    code = _run(analyze, data_dir, tmp_path, "--holdout")

    assert code == 0
    assert len(_log(tmp_path)) == 2
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Nhật ký mở held-out (D-16)" in report
    assert "tuning + held-out (lần mở thứ 2)" in report
    section = report[report.index("## Nhật ký mở held-out (D-16)") :]
    log_lines = [line for line in section.splitlines() if line.startswith("| 20")]
    assert len(log_lines) == 2, "report in toàn bộ log"


def test_the_report_shows_heldout_precision_recall_n_and_status_for_each_rule(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=_flat(DEFAULT_WORDS))

    assert _run(analyze, data_dir, tmp_path, "--holdout") == 1

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    header = next(line for line in report.splitlines() if line.startswith("| Rule |"))
    assert "Held-out P" in header and "Held-out R" in header
    cells = _row(report, "FLAT_PITCH")
    assert "khoá (D-16)" not in cells
    held_precision, held_recall, status = cells[-3], cells[-2], cells[-1]
    assert "n=1" in held_precision and held_precision.startswith("0.00")
    assert "(0/0)" in held_recall  # case correct: không có case nào mong mã chính này
    assert status == "FAIL"
    assert "gate: EVAL FAILED" in report


def test_the_self_compare_baseline_includes_the_heldout_sentence_only_with_the_flag(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=_natural_ref(DEFAULT_WORDS, seed=2))

    assert _run(analyze, data_dir, tmp_path) == 0
    plain = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert _self_split_rows(plain) == ["tuning"]

    assert _run(analyze, data_dir, tmp_path, "--holdout") == 0
    opened = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert sorted(_self_split_rows(opened)) == ["heldout", "tuning"]


def _self_split_rows(report: str) -> list[str]:
    start = report.index("## Mốc tự so (D-18a)")
    end = report.index("\n## ", start + 1)
    rows = [line for line in report[start:end].splitlines() if line.startswith(f"| {LESSON_ID} |")]
    return [row.strip("|").split("|")[2].strip() for row in rows]


def test_a_tuning_run_after_an_opening_leaves_the_log_alone_and_says_how_often_it_was_opened(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _two_sentence_cases(data_dir, tmp_path, heldout_audio=_natural_ref(DEFAULT_WORDS, seed=2))
    assert _run(analyze, data_dir, tmp_path, "--holdout") == 0
    before = (tmp_path / "holdout_log.jsonl").read_bytes()
    capsys.readouterr()

    assert _run(analyze, data_dir, tmp_path) == 0

    assert (tmp_path / "holdout_log.jsonl").read_bytes() == before
    assert "held-out đã mở 1 lần" in capsys.readouterr().out


# --- evalkit.holdout: hàm thuần ----------------------------------------------------------------


def _case(
    case_id: str = "c0001", *, split: str = "heldout", note: str | None = None, segment: int = 0
) -> EvalCase:
    row: dict[str, Any] = {
        "caseId": case_id,
        "lessonId": LESSON_ID,
        "segmentIndex": segment,
        "segStartMs": 100,
        "segEndMs": 2000,
        "segEndExtraMs": 0,
        "segTextHash": "0123456789abcdef",
        "kind": "error",
        "errorType": "flat",
        "split": split,
    }
    if note is not None:
        row["note"] = note
    return EvalCase.model_validate(row)


def test_case_digest_is_stable_and_changes_when_any_label_field_changes(
    holdout: ModuleType,
) -> None:
    base = _case()

    assert holdout.case_digest(base) == holdout.case_digest(_case())
    assert len(holdout.case_digest(base)) == 64
    assert holdout.case_digest(base) != holdout.case_digest(_case(note="đã sửa"))
    assert holdout.case_digest(base) != holdout.case_digest(_case(split="tuning"))


def test_the_default_log_path_is_eval_holdout_log_jsonl(holdout: ModuleType) -> None:
    assert holdout.HOLDOUT_LOG_PATH.parts[-2:] == ("eval", "holdout_log.jsonl")


def test_a_missing_log_reads_as_empty_and_is_not_opened(
    holdout: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "holdout_log.jsonl"

    assert holdout.read_log(path) == []
    assert holdout.is_opened(path) is False


def test_entries_round_trip_with_the_camel_case_keys_of_04_01_e2(holdout: ModuleType) -> None:
    entry = holdout.make_entry(
        [_case("c0001", split="tuning"), _case("c0002")],
        opened_at="2026-10-12T01:02:03Z",
        git_sha="abc123abc123-dirty",
    )

    payload = entry.to_json()

    assert set(payload) == LOG_KEYS
    assert payload["gitSha"] == "abc123abc123-dirty"
    assert payload["splits"] == {"c0001": "tuning", "c0002": "heldout"}
    assert list(payload["digests"]) == ["c0002"]
    assert holdout.HoldoutEntry.from_json(payload) == entry


def test_append_entry_adds_one_line_each_time_and_leaves_no_part_file(
    holdout: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "holdout_log.jsonl"
    first = holdout.make_entry([_case()], opened_at="2026-10-12T01:00:00Z", git_sha="a")
    second = holdout.make_entry([_case()], opened_at="2026-10-12T02:00:00Z", git_sha="b")

    holdout.append_entry(path, first)
    holdout.append_entry(path, second)

    assert holdout.read_log(path) == [first, second]
    assert holdout.is_opened(path) is True
    assert len(path.read_text("utf-8").splitlines()) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["holdout_log.jsonl"]


def test_a_corrupt_log_line_raises_a_log_error_naming_the_line_number(
    holdout: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "holdout_log.jsonl"
    good = holdout.make_entry([_case()], opened_at="2026-10-12T01:00:00Z", git_sha="a")
    holdout.append_entry(path, good)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    with pytest.raises(holdout.HoldoutLogError, match="dòng 2"):
        holdout.read_log(path)


# --- đóng băng nhãn từ lần mở đầu (D-09, D-12) --------------------------------------------------


def _opened_once(data_dir: Path, tmp_path: Path, analyze: ModuleType) -> dict[str, Any]:
    """Bài 3 câu; c0001 tuning (câu 0), c0002 held-out sạch (câu 1); đã mở held-out một lần."""
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS, DEFAULT_WORDS])
    tuning_stem = write_clip(data_dir, LESSON_ID, 0, 1, _flat(DEFAULT_WORDS))
    held_stem = write_clip(data_dir, LESSON_ID, 1, 1, _natural_ref(DEFAULT_WORDS, seed=2))
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(
                lesson, 0, case_id="c0001", kind="error", error_type="flat", clip=tuning_stem
            ),
            case_dict(lesson, 1, case_id="c0002", kind="correct", split="heldout", clip=held_stem),
        ],
    )
    assert _run(analyze, data_dir, tmp_path, "--holdout") == 0
    assert len(_log(tmp_path)) == 1
    return lesson


def _rows(tmp_path: Path) -> list[dict[str, Any]]:
    text = (tmp_path / "cases.jsonl").read_text("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_editing_a_heldout_label_after_the_first_opening_exits_two_naming_the_case_and_d09(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _opened_once(data_dir, tmp_path, analyze)
    rows = _rows(tmp_path)
    rows[1]["note"] = "sửa nhãn sau khi thấy kết quả"
    write_cases(tmp_path / "cases.jsonl", rows)
    report_before = (tmp_path / "report.md").read_bytes()
    capsys.readouterr()

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    err = capsys.readouterr().err
    assert code == 2
    assert "c0002" in err and "D-09" in err
    assert len(_log(tmp_path)) == 1, "không chấm thì không thêm dòng log"
    assert (tmp_path / "report.md").read_bytes() == report_before


@pytest.mark.parametrize(("case_id", "new_split"), [("c0001", "heldout"), ("c0002", "tuning")])
def test_changing_the_split_of_a_case_in_the_first_log_line_exits_two_naming_it(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case_id: str,
    new_split: str,
) -> None:
    _opened_once(data_dir, tmp_path, analyze)
    rows = _rows(tmp_path)
    for row in rows:
        if row["caseId"] == case_id:
            row["split"] = new_split
    write_cases(tmp_path / "cases.jsonl", rows)
    capsys.readouterr()

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    assert code == 2
    assert case_id in capsys.readouterr().err
    assert len(_log(tmp_path)) == 1


def test_deleting_a_case_that_was_in_the_first_log_line_exits_two_naming_it(
    analyze: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _opened_once(data_dir, tmp_path, analyze)
    write_cases(tmp_path / "cases.jsonl", _rows(tmp_path)[:1])
    capsys.readouterr()

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    assert code == 2
    assert "c0002" in capsys.readouterr().err


def test_a_new_heldout_case_is_scored_and_listed_as_added_after_the_first_opening(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    lesson = _opened_once(data_dir, tmp_path, analyze)
    new_stem = write_clip(data_dir, LESSON_ID, 2, 1, _natural_ref(DEFAULT_WORDS, seed=3))
    rows = _rows(tmp_path)
    rows.append(
        case_dict(lesson, 2, case_id="c0003", kind="correct", split="heldout", clip=new_stem)
    )
    write_cases(tmp_path / "cases.jsonl", rows)

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    assert code == 0
    assert len(_log(tmp_path)) == 2
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "đã chấm 3 clip" in report  # c0001, c0002, c0003
    section = report[report.index("Case held-out thêm sau lần mở đầu") :]
    assert "c0003" in section.split("\n## ")[0]


def test_editing_a_tuning_case_after_the_opening_still_runs_normally(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _opened_once(data_dir, tmp_path, analyze)
    rows = _rows(tmp_path)
    rows[0]["note"] = "ghi chú thêm sau"
    rows[0]["alsoPresent"] = [{"errorType": "extra_pause", "wordIndex": 2}]
    write_cases(tmp_path / "cases.jsonl", rows)

    code = _run(analyze, data_dir, tmp_path, "--holdout")

    assert code in (0, 1)
    assert len(_log(tmp_path)) == 2


def test_the_report_says_no_case_was_added_after_the_first_opening_when_none_was(
    analyze: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _opened_once(data_dir, tmp_path, analyze)

    assert _run(analyze, data_dir, tmp_path, "--holdout") == 0

    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    section = report[report.index("Case held-out thêm sau lần mở đầu") :]
    assert "không có" in section.split("\n## ")[0]


# --- evalkit.holdout.check_frozen: hàm thuần -----------------------------------------------------


def _log_with(holdout: ModuleType, tmp_path: Path, cases: list[EvalCase]) -> list[Any]:
    path = tmp_path / "holdout_log.jsonl"
    holdout.append_entry(
        path, holdout.make_entry(cases, opened_at="2026-10-12T01:00:00Z", git_sha="a")
    )
    return holdout.read_log(path)


def test_check_frozen_accepts_an_empty_log_and_returns_nothing(holdout: ModuleType) -> None:
    assert holdout.check_frozen([_case("c0001")], []) == []


def test_check_frozen_lists_heldout_cases_that_are_not_in_the_first_line(
    holdout: ModuleType, tmp_path: Path
) -> None:
    log = _log_with(holdout, tmp_path, [_case("c0001"), _case("c0002", split="tuning")])
    now = [
        _case("c0001"),
        _case("c0002", split="tuning"),
        _case("c0003"),
        _case("c0004", split="tuning"),
    ]

    assert holdout.check_frozen(now, log) == ["c0003"]


@pytest.mark.parametrize(
    "edit",
    [
        pytest.param(lambda c: c.model_copy(update={"note": "sửa"}), id="note"),
        pytest.param(lambda c: c.model_copy(update={"word_index": 3}), id="wordIndex"),
        pytest.param(lambda c: c.model_copy(update={"clip": "x_0001_01"}), id="clip"),
        pytest.param(
            lambda c: c.model_copy(
                update={"also_present": [EvalAlsoPresent.model_validate({"errorType": "flat"})]}
            ),
            id="alsoPresent",
        ),
    ],
)
def test_check_frozen_rejects_any_edit_to_a_heldout_label_naming_case_and_d09(
    holdout: ModuleType, tmp_path: Path, edit: Any
) -> None:
    log = _log_with(holdout, tmp_path, [_case("c0001")])

    with pytest.raises(holdout.HoldoutViolation) as raised:
        holdout.check_frozen([edit(_case("c0001"))], log)

    assert "c0001" in str(raised.value) and "D-09" in str(raised.value)


def test_check_frozen_rejects_a_changed_or_vanished_split(
    holdout: ModuleType, tmp_path: Path
) -> None:
    log = _log_with(holdout, tmp_path, [_case("c0001", split="tuning"), _case("c0002")])

    with pytest.raises(holdout.HoldoutViolation, match="c0001"):
        holdout.check_frozen([_case("c0001", split="heldout"), _case("c0002")], log)
    with pytest.raises(holdout.HoldoutViolation, match="c0002"):
        holdout.check_frozen([_case("c0001", split="tuning")], log)


# --- tag_clips.py also (D-09) ------------------------------------------------------------------


def _tag(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, *args: str, log: bool = True
) -> int:
    argv = ["also", "--cases", str(tmp_path / "cases.jsonl"), "--data-dir", str(data_dir)]
    if log:
        argv += ["--holdout-log", str(tmp_path / "holdout_log.jsonl")]
    return int(tag_clips.main([*argv, *args]))


def _two_cases(data_dir: Path, tmp_path: Path) -> None:
    lesson = write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS])
    write_cases(
        tmp_path / "cases.jsonl",
        [
            case_dict(lesson, 0, case_id="c0001", kind="error", error_type="flat"),
            case_dict(lesson, 1, case_id="c0002", kind="correct", split="heldout"),
        ],
    )


def _open_log(holdout: ModuleType, tmp_path: Path) -> None:
    cases = [_case("c0001", split="tuning"), _case("c0002")]
    holdout.append_entry(
        tmp_path / "holdout_log.jsonl",
        holdout.make_entry(cases, opened_at="2026-10-12T01:00:00Z", git_sha="a"),
    )


def test_also_adds_one_entry_to_a_tuning_case_even_after_the_opening_and_never_twice(
    tag_clips: ModuleType, holdout: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_cases(data_dir, tmp_path)
    _open_log(holdout, tmp_path)
    args = ("--case", "c0001", "--error", "extra_pause", "--word", "2")

    assert _tag(tag_clips, data_dir, tmp_path, *args) == 0
    assert _tag(tag_clips, data_dir, tmp_path, *args) == 0

    row = _rows(tmp_path)[0]
    assert row["alsoPresent"] == [{"errorType": "extra_pause", "wordIndex": 2}]
    assert "null" not in (tmp_path / "cases.jsonl").read_text("utf-8")
    EvalCase.model_validate(row)


def test_also_on_a_heldout_case_works_while_the_log_is_empty(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    _two_cases(data_dir, tmp_path)

    code = _tag(tag_clips, data_dir, tmp_path, "--case", "c0002", "--error", "flat")

    assert code == 0
    assert _rows(tmp_path)[1]["alsoPresent"] == [{"errorType": "flat"}]


def test_also_refuses_a_heldout_case_once_the_log_has_a_line_and_leaves_the_file_alone(
    tag_clips: ModuleType,
    holdout: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _two_cases(data_dir, tmp_path)
    _open_log(holdout, tmp_path)
    before = (tmp_path / "cases.jsonl").read_bytes()

    code = _tag(tag_clips, data_dir, tmp_path, "--case", "c0002", "--error", "flat")

    assert code == 2
    err = capsys.readouterr().err
    assert "D-09" in err and "c0002" in err
    assert (tmp_path / "cases.jsonl").read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--case", "c0001", "--error", "flat", "--word", "2"), id="sentence+word"),
        pytest.param(("--case", "c0001", "--error", "pitch_off"), id="word-level without word"),
        pytest.param(("--case", "c0001", "--error", "pitch_off", "--word", "99"), id="word range"),
        pytest.param(("--case", "c9999", "--error", "flat"), id="unknown case"),
    ],
)
def test_also_rejects_a_bad_entry_with_exit_two_and_writes_nothing(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, args: tuple[str, ...]
) -> None:
    _two_cases(data_dir, tmp_path)
    before = (tmp_path / "cases.jsonl").read_bytes()

    assert _tag(tag_clips, data_dir, tmp_path, *args) == 2
    assert (tmp_path / "cases.jsonl").read_bytes() == before


# --- Makefile ----------------------------------------------------------------------------------


def test_the_makefile_has_the_holdout_variable_the_holdout_branch_and_the_sweep_target() -> None:
    text = (Path(REPO_ROOT) / "Makefile").read_text(encoding="utf-8")
    phony = next(line for line in text.splitlines() if line.startswith(".PHONY:"))

    assert "HOLDOUT ?=" in text
    assert "$(if $(filter 1,$(HOLDOUT)),--holdout)" in text
    assert "eval-sweep" in phony.split()
    assert "\neval-sweep:\n" in text
    assert "eval/sweep.py $(if $(PARAM),--param $(PARAM))" in text

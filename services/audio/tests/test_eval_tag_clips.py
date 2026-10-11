"""`eval/tag_clips.py`: viết kịch bản, chốt split một lần, gắn clip (04-04, EVL-01, EVL-03).

`tag_clips.py` không nằm trong package của service nên được nạp bằng `eval_synth.load_eval`. Mỗi
test dựng một DATA_DIR tạm có bài `ready` tổng hợp và gọi `tag_clips.main([...])`. Hai phần:

- lát đầu-cuối: `add` -> `split` -> `tag --yes` -> `analyze.main` đếm đúng (D-01, D-02, D-12);
- `assign_splits` là hàm thuần nên được kiểm trực tiếp trên bộ 28 câu dựng tay (D-12).
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from eval_synth import (
    DEFAULT_WORDS,
    LESSON_ID,
    OTHER_WORDS,
    clip_stem,
    load_eval,
    load_evalkit,
    sentence_text,
    write_clip,
    write_ready_lesson,
)
from synth import synth_sentence

from audio_service.config import get_settings
from audio_service.contracts_gen import EvalCase


@pytest.fixture
def tag_clips(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_eval("tag_clips", monkeypatch)


@pytest.fixture
def cases_mod(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    return load_evalkit("cases", monkeypatch)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


def _run(tag_clips: ModuleType, data_dir: Path, tmp_path: Path, command: str, *args: str) -> int:
    argv = [command, "--cases", str(tmp_path / "cases.jsonl"), "--data-dir", str(data_dir), *args]
    return int(tag_clips.main(argv))


def _rows(tmp_path: Path) -> list[dict[str, Any]]:
    text = (tmp_path / "cases.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _flat_audio(words: Sequence[Any]) -> Any:
    audio, _ = synth_sentence(list(words), flat_f0=180.0, seed=4)
    return audio


# --- lát đầu-cuối: add -> split -> tag -> analyze -------------------------------------------


def test_add_writes_one_valid_case_line_with_the_next_case_id(
    tag_clips: ModuleType, cases_mod: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir)

    code = _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment", "0",
                "--error", "flat")  # fmt: skip

    assert code == 0
    text = (tmp_path / "cases.jsonl").read_text(encoding="utf-8")
    assert len(text.splitlines()) == 1 and text.endswith("\n")
    assert "null" not in text, "optional là vắng mặt, không bao giờ null"
    case = EvalCase.model_validate_json(text.splitlines()[0])
    row = json.loads(text)
    assert row["caseId"] == "c0001" and row["kind"] == "error" and row["errorType"] == "flat"
    assert "wordIndex" not in row and "split" not in row and "clip" not in row
    assert case.lesson_id == LESSON_ID and case.segment_index == 0
    segment = {
        "start": row["segStartMs"] / 1000,
        "end": row["segEndMs"] / 1000,
        "text": sentence_text(DEFAULT_WORDS),
    }
    assert row["segTextHash"] == cases_mod.text_hash(segment["text"])
    assert row["segEndExtraMs"] == 0


def test_a_second_add_gets_the_following_case_id(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir)
    base = ("add", "--lesson", LESSON_ID, "--segment", "0")
    assert _run(tag_clips, data_dir, tmp_path, *base, "--error", "flat") == 0
    assert _run(tag_clips, data_dir, tmp_path, *base, "--error", "pitch_off", "--word", "2") == 0

    rows = _rows(tmp_path)
    assert [row["caseId"] for row in rows] == ["c0001", "c0002"]
    assert rows[1]["wordIndex"] == 2


def test_split_twice_leaves_the_file_byte_identical_and_every_case_gets_a_side(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])
    for segment in ("0", "1"):
        assert _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment",
                    segment, "--error", "flat") == 0  # fmt: skip

    assert _run(tag_clips, data_dir, tmp_path, "split") == 0
    first = (tmp_path / "cases.jsonl").read_bytes()
    assert _run(tag_clips, data_dir, tmp_path, "split") == 0

    assert (tmp_path / "cases.jsonl").read_bytes() == first
    assert sorted(row["split"] for row in _rows(tmp_path)) == ["heldout", "tuning"]


def test_split_dry_run_prints_the_table_and_writes_nothing(
    tag_clips: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])
    for segment in ("0", "1"):
        assert _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment",
                    segment, "--error", "flat") == 0  # fmt: skip
    before = (tmp_path / "cases.jsonl").read_bytes()
    capsys.readouterr()

    assert _run(tag_clips, data_dir, tmp_path, "split", "--dry-run") == 0

    out = capsys.readouterr().out
    assert "flat" in out and "held-out" in out
    assert (tmp_path / "cases.jsonl").read_bytes() == before


def test_tag_yes_attaches_the_stored_clip_and_a_second_run_changes_nothing(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir)
    assert _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment", "0",
                "--error", "flat") == 0  # fmt: skip
    stem = write_clip(
        data_dir, LESSON_ID, 0, 1, _flat_audio(DEFAULT_WORDS), text=sentence_text(DEFAULT_WORDS)
    )

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0
    assert _rows(tmp_path)[0]["clip"] == stem
    after_first = (tmp_path / "cases.jsonl").read_bytes()

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0
    assert (tmp_path / "cases.jsonl").read_bytes() == after_first


def test_tag_refuses_a_clip_whose_sidecar_text_is_not_the_current_sentence(
    tag_clips: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_ready_lesson(data_dir)
    assert _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment", "0",
                "--error", "flat") == 0  # fmt: skip
    write_clip(data_dir, LESSON_ID, 0, 1, _flat_audio(DEFAULT_WORDS), text="một câu khác")
    before = (tmp_path / "cases.jsonl").read_bytes()

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 2

    assert clip_stem(LESSON_ID, 0, 1) in capsys.readouterr().err
    assert (tmp_path / "cases.jsonl").read_bytes() == before


def test_a_case_written_with_add_split_and_tag_is_counted_by_analyze(
    tag_clips: ModuleType,
    data_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentences = [DEFAULT_WORDS, OTHER_WORDS]
    write_ready_lesson(data_dir, sentences)
    for segment in ("0", "1"):
        assert _run(tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment",
                    segment, "--error", "flat") == 0  # fmt: skip
    assert _run(tag_clips, data_dir, tmp_path, "split") == 0
    tuning = next(row for row in _rows(tmp_path) if row["split"] == "tuning")
    index = tuning["segmentIndex"]
    write_clip(
        data_dir,
        LESSON_ID,
        index,
        1,
        _flat_audio(sentences[index]),
        text=sentence_text(sentences[index]),
    )
    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0
    capsys.readouterr()

    analyze = load_eval("analyze", monkeypatch)
    code = analyze.main(
        [
            "--cases", str(tmp_path / "cases.jsonl"),
            "--report", str(tmp_path / "report.md"),
            "--data-dir", str(data_dir),
        ]
    )  # fmt: skip

    assert code == 0, capsys.readouterr().out
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    row = next(
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in report.splitlines()
        if line.startswith("| FLAT_PITCH |")
    )
    assert row[1] == "1" and row[2] == "0", row  # TP 1, FP 0


# --- assign_splits: hàm thuần (D-12) --------------------------------------------------------

STRATA = (
    "wrong_stress",
    "flat",
    "extra_pause",
    "final_rise",
    "pitch_off",
    "weak_form",
    "final_drop",
    "correct",
)
WORD_LEVEL = {"wrong_stress", "extra_pause", "pitch_off", "weak_form", "final_drop"}


def _case(
    sentence: int, number: int, stratum: str, *, lesson: str = LESSON_ID, split: str | None = None
) -> EvalCase:
    row: dict[str, Any] = {
        "caseId": f"c{sentence:03d}{number}",
        "lessonId": lesson,
        "segmentIndex": sentence,
        "segStartMs": 1000,
        "segEndMs": 3000,
        "segEndExtraMs": 0,
        "segTextHash": "0123456789abcdef",
        "kind": "correct" if stratum == "correct" else "error",
    }
    if stratum != "correct":
        row["errorType"] = stratum
    if stratum in WORD_LEVEL:
        row["wordIndex"] = 1
    if split is not None:
        row["split"] = split
    return EvalCase.model_validate(row)


def _hand_made_set() -> list[EvalCase]:
    """28 câu, mỗi câu 3-4 case ở các tầng khác nhau, xoay vòng trong 7 errorType + `correct`."""
    cases: list[EvalCase] = []
    for sentence in range(28):
        for number in range(3 + sentence % 2):
            cases.append(_case(sentence, number, STRATA[(sentence * 3 + number) % len(STRATA)]))
    return cases


def _stratum(case: EvalCase) -> str:
    return case.error_type.root if case.error_type is not None else "correct"


def _sides(cases_mod: ModuleType, cases: list[EvalCase]) -> dict[tuple[str, int], str]:
    sides: dict[tuple[str, int], str] = cases_mod.assign_splits(cases)
    return sides


def test_assign_splits_does_not_depend_on_the_order_of_the_cases(cases_mod: ModuleType) -> None:
    cases = _hand_made_set()
    expected = _sides(cases_mod, cases)
    shuffled = list(cases)
    random.Random(7).shuffle(shuffled)

    assert _sides(cases_mod, shuffled) == expected


def test_every_case_of_a_sentence_falls_on_the_same_side(cases_mod: ModuleType) -> None:
    cases = _hand_made_set()
    sides = _sides(cases_mod, cases)

    assert set(sides) == {(case.lesson_id, case.segment_index) for case in cases}
    assert set(sides.values()) <= {"tuning", "heldout"}


def test_no_stratum_gets_more_heldout_cases_than_ceil_of_thirty_percent(
    cases_mod: ModuleType,
) -> None:
    cases = _hand_made_set()
    sides = _sides(cases_mod, cases)

    for stratum in STRATA:
        members = [case for case in cases if _stratum(case) == stratum]
        held = [c for c in members if sides[(c.lesson_id, c.segment_index)] == "heldout"]
        assert len(held) <= math.ceil(0.30 * len(members)), stratum


def test_the_share_of_heldout_sentences_stays_between_twenty_and_forty_percent(
    cases_mod: ModuleType,
) -> None:
    sides = _sides(cases_mod, _hand_made_set())

    share = sum(1 for side in sides.values() if side == "heldout") / len(sides)

    assert 0.2 <= share <= 0.4, share


def test_assign_splits_keeps_a_split_already_written_and_only_decides_for_the_rest(
    cases_mod: ModuleType,
) -> None:
    # Mọi câu cũ đã chốt `tuning` (trái với hash): không được đổi, chỉ câu mới được gán.
    settled = [c.model_copy(update={"split": "tuning"}) for c in _hand_made_set()]

    sides = _sides(cases_mod, settled + [_case(42, 0, "flat")])

    assert set(sides) == {(LESSON_ID, 42)}, "chỉ câu chưa có split được gán"


def test_a_sentence_with_one_case_already_settled_gives_the_same_split_to_the_others(
    cases_mod: ModuleType,
) -> None:
    cases = [
        _case(0, 0, "flat", split="heldout"),
        _case(0, 1, "correct"),
        _case(1, 0, "flat"),
        _case(1, 1, "correct"),
    ]

    sides = _sides(cases_mod, cases)

    assert sides[(LESSON_ID, 0)] == "heldout"


def test_a_sentence_added_after_the_split_is_heldout_only_below_the_share(
    cases_mod: ModuleType,
) -> None:
    settled = [_case(0, 0, "flat", split="tuning")]
    below = next(i for i in range(1, 500) if cases_mod.split_fraction(LESSON_ID, i) < 0.30)
    above = next(i for i in range(1, 500) if cases_mod.split_fraction(LESSON_ID, i) >= 0.30)

    assert cases_mod.split_for_new_case(settled, LESSON_ID, below) == "heldout"
    assert cases_mod.split_for_new_case(settled, LESSON_ID, above) == "tuning"
    assert cases_mod.split_for_new_case(settled, LESSON_ID, 0) == "tuning"
    assert cases_mod.split_for_new_case([_case(0, 0, "flat")], LESSON_ID, below) is None


def test_split_fraction_is_the_sha256_prefix_of_lesson_and_segment(cases_mod: ModuleType) -> None:
    import hashlib

    digest = hashlib.sha256(f"{LESSON_ID}:3".encode()).hexdigest()[:16]

    assert cases_mod.split_fraction(LESSON_ID, 3) == int(digest, 16) / 16**16
    assert 0.0 <= cases_mod.split_fraction(LESSON_ID, 3) < 1.0

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
from dataclasses import replace
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
    sentences = [DEFAULT_WORDS, DEFAULT_WORDS]  # cùng giọng: clip phẳng đúng với cả hai phía
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


# --- words ----------------------------------------------------------------------------------


def _repeated_word_sentence() -> tuple[Any, ...]:
    """5 từ, từ 1 và từ 3 cùng chữ `bravo`."""
    return (*DEFAULT_WORDS[:3], replace(DEFAULT_WORDS[3], text="bravo"), DEFAULT_WORDS[4])


def test_words_without_a_lesson_lists_the_ready_lessons(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS, OTHER_WORDS])

    assert _run(tag_clips, data_dir, tmp_path, "words") == 0

    out = capsys.readouterr().out
    assert LESSON_ID in out and "Synthetic" in out and "2" in out


def test_words_with_a_lesson_lists_sentences_and_marks_the_short_ones(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS[:4]])

    assert _run(tag_clips, data_dir, tmp_path, "words", "--lesson", LESSON_ID) == 0

    lines = capsys.readouterr().out.splitlines()
    long_line = next(line for line in lines if line.startswith("#0"))
    short_line = next(line for line in lines if line.startswith("#1"))
    assert "(5 từ)" in long_line and sentence_text(DEFAULT_WORDS) in long_line
    assert "(4 từ)" in short_line and "dưới 5 từ" in short_line
    assert "dưới 5 từ" not in long_line


def test_words_of_one_segment_numbers_each_word_and_marks_repeated_words(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir, [_repeated_word_sentence()])

    assert (
        _run(tag_clips, data_dir, tmp_path, "words", "--lesson", LESSON_ID, "--segment", "0") == 0
    )

    lines = capsys.readouterr().out.splitlines()
    assert any(line.startswith("0: alpha") and "trùng" not in line for line in lines)
    assert any(line.startswith("1: bravo") and "trùng" in line for line in lines)
    assert any(line.startswith("3: bravo") and "trùng" in line for line in lines)


# --- add: các lối từ chối --------------------------------------------------------------------


def _add(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, *args: str, segment: str = "0"
) -> int:
    return _run(
        tag_clips, data_dir, tmp_path, "add", "--lesson", LESSON_ID, "--segment", segment, *args
    )


@pytest.mark.parametrize(
    "args",
    [
        ("--error", "flat", "--word", "2"),  # mức câu không có wordIndex
        ("--error", "pitch_off"),  # lỗi theo từ thiếu wordIndex
        ("--correct", "--word", "1"),  # case đúng không có wordIndex
        ("--error", "pitch_off", "--word", "9"),  # wordIndex ngoài câu
        ("--error", "wrong_stress", "--word", "1"),  # B1-a: chữ xuất hiện hơn một lần
        ("--error", "flat", "--correct"),  # vừa lỗi vừa đúng
        (),  # không nói gì
    ],
    ids=[
        "flat+word",
        "pitch_off-no-word",
        "correct+word",
        "word-outside",
        "b1a",
        "both",
        "neither",
    ],
)
def test_add_refuses_an_invalid_case_and_leaves_the_file_alone(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, args: tuple[str, ...]
) -> None:
    write_ready_lesson(data_dir, [_repeated_word_sentence()])

    assert _add(tag_clips, data_dir, tmp_path, *args) == 2

    assert not (tmp_path / "cases.jsonl").exists()


def test_add_refuses_a_sentence_with_fewer_than_five_words(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS[:4]])

    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat") == 2

    assert "5" in capsys.readouterr().err and not (tmp_path / "cases.jsonl").exists()


def test_add_accepts_wrong_stress_on_a_word_that_appears_once(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir, [_repeated_word_sentence()])

    assert _add(tag_clips, data_dir, tmp_path, "--error", "wrong_stress", "--word", "2") == 0

    assert _rows(tmp_path)[0]["wordIndex"] == 2


def test_add_after_the_split_inherits_or_decides_the_split_of_a_new_case(
    tag_clips: ModuleType, cases_mod: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS] * 3)
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat", segment="0") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat", segment="1") == 0
    assert _run(tag_clips, data_dir, tmp_path, "split") == 0
    settled = {row["segmentIndex"]: row["split"] for row in _rows(tmp_path)}

    assert _add(tag_clips, data_dir, tmp_path, "--correct", segment="0") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--correct", segment="2") == 0

    rows = _rows(tmp_path)
    assert rows[2]["split"] == settled[0], "câu đã chốt: case mới theo câu"
    expected = "heldout" if cases_mod.split_fraction(LESSON_ID, 2) < 0.30 else "tuning"
    assert rows[3]["split"] == expected, "câu mới sau khi chốt: theo D2"


# --- tag tương tác ----------------------------------------------------------------------------


class _Answers:
    """`ask` giả lập: trả lần lượt các câu trả lời và ghi lại lời nhắc."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str = "") -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


def _three_waiting_cases(tag_clips: ModuleType, data_dir: Path, tmp_path: Path) -> list[str]:
    """Một câu, ba case đang chờ (flat, pitch_off@2, extra_pause@1) và ba clip lưu theo thứ tự."""
    write_ready_lesson(data_dir)
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--error", "pitch_off", "--word", "2") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--error", "extra_pause", "--word", "1") == 0
    text = sentence_text(DEFAULT_WORDS)
    return [
        write_clip(data_dir, LESSON_ID, 0, attempt, _flat_audio(DEFAULT_WORDS), text=text)
        for attempt in (1, 2, 3)
    ]


def _tag_argv(data_dir: Path, tmp_path: Path) -> list[str]:
    return ["tag", "--cases", str(tmp_path / "cases.jsonl"), "--data-dir", str(data_dir)]


def test_interactive_tag_assigns_the_chosen_case_skips_and_quits(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stems = _three_waiting_cases(tag_clips, data_dir, tmp_path)
    ask = _Answers("2", "s", "q")

    assert tag_clips.main(_tag_argv(data_dir, tmp_path), ask=ask) == 0

    assert [row.get("clip") for row in _rows(tmp_path)] == [None, stems[0], None]
    out = capsys.readouterr().out
    assert stems[0] in out and "pitch_off@2" in out and "charlie" in out
    for hidden in ("overall", "điểm", "issue", "FLAT_PITCH"):
        assert hidden not in out, "không hiển thị điểm hay issue của hệ thống (D-01)"
    assert len(ask.prompts) == 3


def test_interactive_tag_takes_the_first_waiting_case_on_an_empty_answer(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    stems = _three_waiting_cases(tag_clips, data_dir, tmp_path)

    assert tag_clips.main(_tag_argv(data_dir, tmp_path), ask=_Answers("", "q")) == 0

    assert [row.get("clip") for row in _rows(tmp_path)] == [stems[0], None, None]


def test_interactive_tag_asks_again_after_an_answer_it_does_not_understand(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path
) -> None:
    stems = _three_waiting_cases(tag_clips, data_dir, tmp_path)
    ask = _Answers("9", "x", "3", "q")

    assert tag_clips.main(_tag_argv(data_dir, tmp_path), ask=ask) == 0

    assert [row.get("clip") for row in _rows(tmp_path)] == [None, None, stems[0]]


def test_tag_warns_about_a_clip_with_no_waiting_case_and_still_succeeds(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS])
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat", segment="0") == 0
    stem = write_clip(
        data_dir, LESSON_ID, 1, 1, _flat_audio(DEFAULT_WORDS), text=sentence_text(DEFAULT_WORDS)
    )
    before = (tmp_path / "cases.jsonl").read_bytes()

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0

    assert stem in capsys.readouterr().out
    assert (tmp_path / "cases.jsonl").read_bytes() == before


def test_tag_skips_a_clip_whose_sidecar_is_missing(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stems = _three_waiting_cases(tag_clips, data_dir, tmp_path)
    (data_dir / "eval_clips" / f"{stems[0]}.json").unlink()

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0

    assert stems[0] in capsys.readouterr().err
    assert [row.get("clip") for row in _rows(tmp_path)] == [stems[1], stems[2], None]


def test_tag_refuses_a_stray_file_name_in_eval_clips(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir)
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat") == 0
    clips = data_dir / "eval_clips"
    clips.mkdir()
    (clips / "stray.wav").write_bytes(b"RIFF")

    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 2

    assert "stray" in capsys.readouterr().err


# --- check ------------------------------------------------------------------------------------


def _scripted_set(tag_clips: ModuleType, data_dir: Path, tmp_path: Path) -> None:
    """2 câu đã chốt split: 2 case flat ở câu 0 (cùng có clip, một nhóm retest), 1 case correct
    ở câu 1 chưa gắn clip, và một clip của câu 1 chưa được gắn."""
    write_ready_lesson(data_dir, [DEFAULT_WORDS, DEFAULT_WORDS])
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat", segment="0") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat", segment="0") == 0
    assert _add(tag_clips, data_dir, tmp_path, "--correct", segment="1") == 0
    assert _run(tag_clips, data_dir, tmp_path, "split") == 0
    text = sentence_text(DEFAULT_WORDS)
    for attempt in (1, 2):
        write_clip(data_dir, LESSON_ID, 0, attempt, _flat_audio(DEFAULT_WORDS), text=text)
    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0
    write_clip(data_dir, LESSON_ID, 1, 1, _flat_audio(DEFAULT_WORDS), text=text)


def test_check_prints_the_coverage_table_and_exits_zero(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _scripted_set(tag_clips, data_dir, tmp_path)
    capsys.readouterr()

    assert _run(tag_clips, data_dir, tmp_path, "check") == 0

    out = capsys.readouterr().out
    flat = next(line for line in out.splitlines() if line.startswith("flat"))
    assert "2/2" in flat, flat
    correct = next(line for line in out.splitlines() if line.startswith("correct"))
    assert "1/0" in correct, correct
    assert "tuning" in out and "heldout" in out
    assert "nhóm retest: 1" in out
    assert "clip chưa gắn: 1" in out


def test_check_exits_two_and_names_the_case_when_the_sentence_stamp_is_wrong(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir)
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat") == 0
    path = tmp_path / "cases.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    row["segTextHash"] = "0" * 16
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    assert _run(tag_clips, data_dir, tmp_path, "check") == 2

    assert "c0001" in capsys.readouterr().err


def test_check_exits_one_when_a_coverage_threshold_is_not_met(
    tag_clips: ModuleType, data_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_ready_lesson(data_dir)
    assert _add(tag_clips, data_dir, tmp_path, "--error", "flat") == 0
    write_clip(
        data_dir, LESSON_ID, 0, 1, _flat_audio(DEFAULT_WORDS), text=sentence_text(DEFAULT_WORDS)
    )
    assert _run(tag_clips, data_dir, tmp_path, "tag", "--yes") == 0
    capsys.readouterr()

    assert _run(tag_clips, data_dir, tmp_path, "check", "--min-error", "1") == 0
    assert _run(tag_clips, data_dir, tmp_path, "check", "--min-error", "2") == 1
    assert "clip lỗi" in capsys.readouterr().out
    assert _run(tag_clips, data_dir, tmp_path, "check", "--min-correct", "1") == 1
    assert _run(tag_clips, data_dir, tmp_path, "check", "--min-per-type", "1") == 1
    assert _run(tag_clips, data_dir, tmp_path, "check", "--min-retest", "1") == 1


# --- Makefile ---------------------------------------------------------------------------------


def test_makefile_has_the_eval_tag_target() -> None:
    from audio_service.config import REPO_ROOT

    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    phony = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))

    assert "eval-tag" in phony.split()
    assert "\neval-tag:\n" in makefile
    assert "eval/tag_clips.py tag" in makefile

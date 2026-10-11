"""Viết kịch bản, chốt split và gắn clip cho bộ eval nội bộ (Phase 4, EVL-01, EVL-03).

    uv run --project services/audio --frozen python eval/tag_clips.py <lệnh> [tuỳ chọn]

Lệnh (cờ chung: `--cases eval/cases.jsonl`, `--data-dir PATH`):

- `words [--lesson L [--segment N]]`: xem bài, câu và chỉ số từ (từ trùng chữ được đánh dấu).
- `add --lesson L --segment N --error TYPE [--word I] | --correct [--note ...]`: ghi thêm một case
  VÀO KỊCH BẢN, trước khi nói (D-02). Dấu nhận diện câu lấy từ bài thật (D-05).
- `split [--dry-run]`: chốt `tuning` / `heldout` một lần (D-12); chạy lại không đổi gì đã ghi.
- `tag [--yes]`: ghép clip đã lưu bằng nút "Lưu clip cho eval" với case đang chờ (D-01). Hỏi từng
  clip (số, Enter = case chờ đầu, `s` bỏ qua, `q` dừng); `--yes` luôn lấy case chờ đầu theo file.
- `check [--min-error N] [--min-per-type N] [--min-correct N] [--min-retest N]`: kiểm mọi case và
  in bảng phủ errorType x split; thiếu ngưỡng nào thì thoát 1.

Chỉ ghi `eval/cases.jsonl` (hoặc file `--cases`), atomic; DATA_DIR chỉ được đọc. Không bao giờ in
điểm hay issue của hệ thống và không suy nhãn từ output của hệ thống (D-01). Không có UI nào được
thêm vào app.

Thoát 0 (xong), 1 (một ngưỡng phủ chưa đạt), 2 (tham số hoặc dữ liệu sai: bất biến case, câu dưới 5
từ, dấu nhận diện lệch, clip hoặc sidecar lạ).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

ERROR_TYPES = (
    "wrong_stress",
    "flat",
    "extra_pause",
    "final_rise",
    "pitch_off",
    "weak_form",
    "final_drop",
)

Ask = Callable[[str], str]


def _common() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--cases", type=Path, help="cases.jsonl (mặc định: eval/cases.jsonl)")
    common.add_argument("--data-dir", type=Path, help="DATA_DIR (mặc định: theo cấu hình app)")
    return common


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Viết kịch bản, chốt split và gắn clip cho bộ eval nội bộ."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    common = _common()

    add = commands.add_parser("add", parents=[common], help="viết một case vào kịch bản")
    add.add_argument("--lesson", required=True, help="id bài (ULID)")
    add.add_argument("--segment", required=True, type=int, help="số thứ tự câu, từ 0")
    add.add_argument("--error", choices=ERROR_TYPES, help="loại lỗi Liam sẽ cố ý nói")
    add.add_argument("--correct", action="store_true", help="case nói đúng (không lỗi)")
    add.add_argument("--word", type=int, help="chỉ số từ (bắt buộc với lỗi theo từ)")
    add.add_argument("--note", help="ghi chú tự do")

    split = commands.add_parser("split", parents=[common], help="chốt tuning/held-out một lần")
    split.add_argument("--dry-run", action="store_true", help="chỉ in, không ghi")

    tag = commands.add_parser("tag", parents=[common], help="ghép clip đã lưu với case đang chờ")
    tag.add_argument("--yes", action="store_true", help="lấy case chờ đầu tiên, không hỏi")

    words = commands.add_parser("words", parents=[common], help="xem bài, câu và chỉ số từ")
    words.add_argument("--lesson", help="id bài; bỏ trống để liệt kê các bài ready")
    words.add_argument("--segment", type=int, help="số thứ tự câu: liệt kê từng từ của câu")

    check = commands.add_parser("check", parents=[common], help="kiểm case và in bảng phủ")
    check.add_argument("--min-error", type=int, default=0, help="số clip lỗi đã gắn tối thiểu")
    check.add_argument("--min-per-type", type=int, default=0, help="số clip đã gắn mỗi errorType")
    check.add_argument("--min-correct", type=int, default=0, help="số clip `correct` đã gắn")
    check.add_argument("--min-retest", type=int, default=0, help="số nhóm retest (>= 2 clip)")
    return parser


class _Toolkit:
    """Các module cần DATA_DIR đã đặt xong: nạp sau khi biến môi trường được đặt (như analyze)."""

    def __init__(self) -> None:
        from evalkit import cases, rescore

        from audio_service import config
        from audio_service.lesson import store
        from audio_service.scoring.thresholds import STRESS_MIN_WORDS

        config.get_settings.cache_clear()
        self.cases = cases
        self.rescore = rescore
        self.config = config
        self.store = store
        self.min_words = STRESS_MIN_WORDS


def _table(header: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    cells = [[str(cell) for cell in row] for row in [header, *rows]]
    widths = [max(len(row[i]) for row in cells) for i in range(len(header))]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in cells]
    return "\n".join(line.rstrip() for line in lines)


def _lesson(kit: _Toolkit, lesson_id: str, index: int | None = None) -> Any:
    """Bài `ready` đọc từ DATA_DIR; `index` (nếu có) phải nằm trong bài."""
    try:
        lesson = kit.store.load_lesson(lesson_id)
    except (kit.config.InvalidIdError, OSError, ValueError):
        raise kit.rescore.DataError(f"không đọc được bài {lesson_id} trong DATA_DIR") from None
    if lesson.status != "ready":
        raise kit.rescore.DataError(f"bài {lesson_id} chưa ở trạng thái ready ({lesson.status})")
    if index is not None and not 0 <= index < len(lesson.segments):
        raise kit.rescore.DataError(f"bài {lesson_id} không có câu {index}")
    return lesson


def _load(kit: _Toolkit, path: Path, *, allow_missing: bool = False) -> list[Any]:
    if allow_missing and not path.exists():
        return []
    cases = kit.cases.load_cases(path)
    kit.cases.validate_cases(cases)
    return cases


def _describe(kit: _Toolkit, case: Any, words: Sequence[str] | None = None) -> str:
    """`errorType@wordIndex "chữ"` hoặc `correct`; không bao giờ có điểm hay issue."""
    if case.kind == "correct":
        return "correct"
    label = kit.cases.error_type_of(case) or "?"
    if case.word_index is None:
        return label
    spoken = f' "{words[case.word_index]}"' if words and case.word_index < len(words) else ""
    return f"{label}@{case.word_index}{spoken}"


# --- add ---------------------------------------------------------------------------------------


def _build_case(kit: _Toolkit, args: argparse.Namespace, existing: Sequence[Any]) -> Any:
    from audio_service.contracts_gen import EvalCase

    if args.correct == (args.error is not None):
        raise kit.cases.CaseError("chọn đúng một trong --error TYPE hoặc --correct")
    if args.correct and args.word is not None:
        raise kit.cases.CaseError("case nói đúng (--correct) không có --word")
    if args.word is not None and args.word < 0:
        raise kit.cases.CaseError("--word phải >= 0")

    lesson = _lesson(kit, args.lesson, args.segment)
    segment = lesson.segments[args.segment]
    words = [word.text for word in segment.words]
    if len(words) < kit.min_words:
        raise kit.cases.CaseError(
            f"câu {args.segment} chỉ có {len(words)} từ, cần >= {kit.min_words} (D-11)"
        )

    if args.error is not None:
        if args.error in kit.cases.WORD_LEVEL_TYPES and args.word is None:
            raise kit.cases.CaseError(f"errorType {args.error} bắt buộc có --word")
        if args.error in kit.cases.SENTENCE_LEVEL_TYPES and args.word is not None:
            raise kit.cases.CaseError(f"errorType {args.error} ở mức câu, không có --word")
    if args.word is not None:
        if args.word >= len(words):
            raise kit.cases.CaseError(f"--word {args.word} ngoài câu ({len(words)} từ)")
        if args.error == "wrong_stress" and words.count(words[args.word]) > 1:
            raise kit.cases.CaseError(
                f'wrong_stress: chữ "{words[args.word]}" xuất hiện hơn một lần trong câu; '
                "không đối chiếu được từ bị nhấn sai theo chữ (B1-a)"
            )

    row: dict[str, Any] = {
        "caseId": kit.cases.next_case_id(existing),
        "lessonId": lesson.id,
        "segmentIndex": args.segment,
        **kit.cases.stamp_for(segment),
        "kind": "correct" if args.correct else "error",
    }
    optional: dict[str, Any] = {
        "errorType": args.error,
        "wordIndex": args.word,
        "split": kit.cases.split_for_new_case(existing, lesson.id, args.segment),
        "note": args.note,
    }
    row.update({key: value for key, value in optional.items() if value is not None})
    return EvalCase.model_validate(row)


def _cmd_add(kit: _Toolkit, args: argparse.Namespace, path: Path) -> int:
    existing = _load(kit, path, allow_missing=True)
    case = _build_case(kit, args, existing)
    kit.cases.write_cases(path, [*existing, case])
    print(kit.cases.dump_case(case))
    return 0


# --- split -------------------------------------------------------------------------------------


def _split_table(kit: _Toolkit, cases: Sequence[Any]) -> str:
    totals: dict[str, int] = {}
    held: dict[str, int] = {}
    for case in cases:
        name = kit.cases.stratum(case)
        totals[name] = totals.get(name, 0) + 1
        if case.split == "heldout":
            held[name] = held.get(name, 0) + 1
    rows = [
        (name, total, held.get(name, 0), f"{held.get(name, 0) / total:.0%}")
        for name, total in sorted(totals.items())
    ]
    sentences = {(case.lesson_id, case.segment_index): case.split for case in cases}
    n_held = sum(1 for side in sentences.values() if side == "heldout")
    share = f"{n_held / len(sentences):.0%}" if sentences else "-"
    table = _table(("tầng", "tổng", "held-out", "tỉ lệ"), rows)
    return f"{table}\ncâu held-out: {n_held}/{len(sentences)} ({share})"


def _cmd_split(kit: _Toolkit, args: argparse.Namespace, path: Path) -> int:
    cases = _load(kit, path)
    sides = kit.cases.assign_splits(cases)
    updated = kit.cases.with_splits(cases, sides)
    if sides:
        verb = "sẽ chốt" if args.dry_run else "đã chốt"
        print(f"{verb} split cho {len(sides)} câu")
    else:
        print("không có câu nào cần chốt split")
    print(_split_table(kit, updated))
    if sides and not args.dry_run:
        kit.cases.write_cases(path, updated)
    return 0


# --- tag ---------------------------------------------------------------------------------------


def _sidecar(wav: Path, stem: str, kit: _Toolkit) -> dict[str, Any] | None:
    """Sidecar cùng tên; thiếu hoặc hỏng -> None (báo và bỏ qua clip). Lệch stem -> DataError."""
    try:
        data = json.loads(wav.with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        not isinstance(data, dict)
        or data.get("lessonId") != stem[:26]
        or data.get("segmentIndex") != int(stem[27:31])
        or not isinstance(data.get("text"), str)
    ):
        raise kit.rescore.DataError(f"sidecar của clip {stem} không khớp tên clip")
    return data


def _pending(cases: Sequence[Any], lesson_id: str, index: int) -> list[int]:
    return [
        position
        for position, case in enumerate(cases)
        if case.lesson_id == lesson_id and case.segment_index == index and case.clip is None
    ]


Choice = int | Literal["skip", "quit"]


def _choose(
    kit: _Toolkit,
    ask: Ask,
    stem: str,
    cases: Sequence[Any],
    waiting: Sequence[int],
    words: Sequence[str],
) -> Choice:
    """Hỏi Liam clip này thuộc case chờ nào: số, Enter (= 1), `s` bỏ qua, `q` dừng.

    Chỉ hiện chữ của câu, loại lỗi, vị trí từ và ghi chú đã viết trước khi nói; không có điểm hay
    issue của hệ thống (D-01).
    """
    print(f"clip {stem} (lượt {int(stem[32:])}): {' '.join(words)}")
    for number, position in enumerate(waiting, start=1):
        case = cases[position]
        note = f"  ghi chú: {case.note}" if case.note else ""
        print(f"  {number}. {case.case_id}  {_describe(kit, case, words)}{note}")
    while True:
        try:
            answer = ask("Chọn case (Enter = 1, s = bỏ qua, q = dừng): ").strip().lower()
        except EOFError:
            return "quit"
        if answer == "":
            return waiting[0]
        if answer in ("s", "q"):
            return "skip" if answer == "s" else "quit"
        if answer.isdigit() and 1 <= int(answer) <= len(waiting):
            return waiting[int(answer) - 1]
        print(f"không hiểu {answer!r}: nhập số từ 1 đến {len(waiting)}, Enter, s hoặc q")


def _cmd_tag(kit: _Toolkit, args: argparse.Namespace, path: Path, ask: Ask) -> int:
    cases = _load(kit, path)
    clips = kit.rescore.clips_root()
    if not clips.is_dir():
        print(f"chưa có thư mục eval_clips trong DATA_DIR ({clips.name})")
        return 0

    base = clips.resolve()
    attached = 0
    for wav in sorted(clips.glob("*.wav")):
        stem = wav.stem
        if any(case.clip == stem for case in cases):
            continue
        if not kit.rescore.CLIP_STEM_RE.fullmatch(stem) or not wav.resolve().is_relative_to(base):
            raise kit.rescore.DataError(f"tên clip lạ trong eval_clips: {stem!r} (T-04-09)")
        sidecar = _sidecar(wav, stem, kit)
        if sidecar is None:
            print(f"bỏ qua {stem}: thiếu hoặc hỏng sidecar", file=sys.stderr)
            continue
        lesson_id, index = stem[:26], int(stem[27:31])
        waiting = _pending(cases, lesson_id, index)
        if not waiting:
            print(f"bỏ qua {stem}: chưa có case chờ cho câu này (viết bằng add trước)")
            continue

        segment = _lesson(kit, lesson_id, index).segments[index]
        if sidecar["text"] != segment.text:
            raise kit.rescore.DataError(
                f"clip {stem}: câu đã đổi so với lúc thu (D-05); không gắn nhãn cho clip này"
            )
        words = [word.text for word in segment.words]
        chosen: Choice = waiting[0] if args.yes else _choose(kit, ask, stem, cases, waiting, words)
        if chosen == "quit":
            break
        if chosen == "skip":
            continue
        mismatch = kit.cases.stamp_mismatch(cases[chosen], segment)
        if mismatch is not None:
            raise kit.rescore.DataError(
                f"{cases[chosen].case_id}: câu đã đổi so với lúc viết case ({mismatch}) (D-05)"
            )
        cases = [
            case.model_copy(update={"clip": stem}) if position == chosen else case
            for position, case in enumerate(cases)
        ]
        kit.cases.write_cases(path, cases)
        attached += 1
        print(f"{stem} -> {cases[chosen].case_id} ({_describe(kit, cases[chosen], words)})")
    print(f"đã gắn {attached} clip")
    return 0


# --- words -------------------------------------------------------------------------------------


def _cmd_words(kit: _Toolkit, args: argparse.Namespace) -> int:
    if args.lesson is None:
        ready = [lesson for lesson in kit.store.iter_lessons() if lesson.status == "ready"]
        if not ready:
            print("chưa có bài nào ở trạng thái ready trong DATA_DIR")
            return 0
        rows = [(lesson.id, lesson.title, f"{len(lesson.segments)} câu") for lesson in ready]
        print(_table(("id", "tiêu đề", "số câu"), rows))
        return 0

    lesson = _lesson(kit, args.lesson, args.segment)
    if args.segment is None:
        for segment in lesson.segments:
            count = len(segment.words)
            short = f"  [dưới {kit.min_words} từ]" if count < kit.min_words else ""
            span = f"{segment.start:.2f}–{segment.end:.2f}"
            print(f"#{segment.index}  {span}  ({count} từ)  {segment.text}{short}")
        return 0

    texts = [word.text for word in lesson.segments[args.segment].words]
    for position, text in enumerate(texts):
        repeated = "  ← trùng chữ với từ khác" if texts.count(text) > 1 else ""
        print(f"{position}: {text}{repeated}")
    return 0


# --- check -------------------------------------------------------------------------------------


def _coverage_table(kit: _Toolkit, cases: Sequence[Any]) -> str:
    """Bảng errorType x split; mỗi ô là `tổng/đã gắn clip`."""
    counts: dict[tuple[str, str], list[int]] = {}
    for case in cases:
        cell = counts.setdefault((kit.cases.stratum(case), str(case.split or "none")), [0, 0])
        cell[0] += 1
        cell[1] += 1 if case.clip is not None else 0
    rows = []
    for name in (*ERROR_TYPES, "correct"):
        cells = [counts.get((name, side), [0, 0]) for side in ("tuning", "heldout", "none")]
        total = sum(cell[0] for cell in cells)
        rows.append((name, *(f"{cell[0]}/{cell[1]}" for cell in cells), total))
    return _table(("tầng", "tuning", "heldout", "chưa chốt", "tổng"), rows)


def _retest_groups(cases: Sequence[Any]) -> int:
    """Nhóm (bài, câu, kind, errorType, wordIndex) có >= 2 clip đã gắn (04-01 mục J)."""
    sizes: dict[tuple[Any, ...], int] = {}
    for case in cases:
        if case.clip is not None:
            error_type = case.error_type.root if case.error_type is not None else None
            key = (case.lesson_id, case.segment_index, case.kind, error_type, case.word_index)
            sizes[key] = sizes.get(key, 0) + 1
    return sum(1 for size in sizes.values() if size >= 2)


def _cmd_check(kit: _Toolkit, args: argparse.Namespace, path: Path) -> int:
    cases = _load(kit, path)
    lessons = kit.rescore.load_lessons(cases)
    kit.rescore.check_identity(cases, lessons)
    for case in cases:
        count = len(lessons[case.lesson_id].segments[case.segment_index].words)
        if count < kit.min_words:
            raise kit.cases.CaseError(
                f"{case.case_id}: câu chỉ có {count} từ, cần >= {kit.min_words} (D-11)"
            )

    attached = {case.clip for case in cases if case.clip is not None}
    clips = kit.rescore.clips_root()
    stems = {wav.stem for wav in clips.glob("*.wav")} if clips.is_dir() else set()
    groups = _retest_groups(cases)

    print(f"{len(cases)} case hợp lệ (ô = tổng/đã gắn clip)")
    print(_coverage_table(kit, cases))
    print(f"clip chưa gắn: {len(stems - attached)}")
    print(f"nhóm retest: {groups}")

    tagged = [case for case in cases if case.clip is not None]
    per_type = {name: 0 for name in ERROR_TYPES}
    for case in tagged:
        if case.kind == "error":
            per_type[kit.cases.error_type_of(case) or ""] += 1
    n_errors = sum(per_type.values())
    n_correct = len(tagged) - n_errors
    missing = []
    if n_errors < args.min_error:
        missing.append(f"clip lỗi đã gắn: {n_errors} < {args.min_error}")
    missing += [
        f"clip {name} đã gắn: {count} < {args.min_per_type}"
        for name, count in per_type.items()
        if count < args.min_per_type
    ]
    if n_correct < args.min_correct:
        missing.append(f"clip correct đã gắn: {n_correct} < {args.min_correct}")
    if groups < args.min_retest:
        missing.append(f"nhóm retest: {groups} < {args.min_retest}")
    if missing:
        print("CHƯA ĐỦ PHỦ:")
        for line in missing:
            print(f"  - {line}")
        return 1
    print("CHECK OK")
    return 0


# --- điều phối ---------------------------------------------------------------------------------


def _run(args: argparse.Namespace, root: Path, ask: Ask) -> int:
    if args.data_dir is not None:
        if not args.data_dir.is_dir():
            print(f"--data-dir không phải thư mục: {args.data_dir}", file=sys.stderr)
            return 2
        os.environ["DATA_DIR"] = str(args.data_dir)
        # settings.json của app có thể ghi đè DATA_DIR; trỏ cấu hình vào chỗ trống để --data-dir
        # thắng.
        os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")

    kit = _Toolkit()
    path = args.cases if args.cases is not None else kit.cases.CASES_PATH
    try:
        if args.command == "add":
            return _cmd_add(kit, args, path)
        if args.command == "split":
            return _cmd_split(kit, args, path)
        if args.command == "words":
            return _cmd_words(kit, args)
        if args.command == "check":
            return _cmd_check(kit, args, path)
        return _cmd_tag(kit, args, path, ask)
    except (kit.cases.CaseError, kit.rescore.DataError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def main(argv: Sequence[str] | None = None, *, ask: Ask = input) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="shadowenglab-tag-"))
    try:
        return _run(args, root, ask)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)

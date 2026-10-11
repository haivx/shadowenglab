"""Quét ngưỡng trên tập tuning và đề xuất giá trị (Phase 4, EVL-04, D-13).

    uv run --project services/audio --frozen python eval/sweep.py \
        [--param NAME ...] [--cases eval/cases.jsonl] [--data-dir PATH] [--min-precision 0.95]

Với mỗi tham số trong `SWEEP_GRID` (lưới do Liam duyệt ở 04-01 mục G), chấm lại mọi clip tuning và
mọi mốc tự so của câu tuning ở từng giá trị, các tham số khác giữ nguyên, rồi in một dòng
TP/FP/P/CI95/R/n cho mỗi giá trị và một dòng "Đề xuất <THAM SỐ> = <giá trị>": giá trị có recall cao
nhất trong các giá trị có precision tuning >= `--min-precision` (mặc định 0.95), hoà thì chọn giá
trị gần giá trị hiện tại; không có thì "không có giá trị đạt 95 %".

CHỈ in stdout. Không ghi `thresholds.py` hay file nào khác: Liam đọc bảng, chọn giá trị và tự sửa
`thresholds.py` rồi tăng `THRESHOLDS_VERSION` (D-13). Ghi đè chỉ sống trong bộ nhớ của process này
(`evalkit.overrides`) và được khôi phục sau mỗi giá trị.

CHỈ tuning: không có cờ nào để bật held-out (D-16); WAV của case held-out không bao giờ được đọc.
Case thiếu `split` làm script thoát 2 (D-12).

Thoát 0, hoặc 2 khi tham số/dữ liệu sai (tham số lạ, thiếu file, lệch dấu nhận diện câu D-05...).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from evalkit.counting import Observation, RuleTally, tally, wilson

if TYPE_CHECKING:
    from audio_service.scoring.scorer import ProsodyScore

MIN_PRECISION = 0.95  # D-13: biên 95 % ở tuning cho kỳ vọng held-out >= 90 %

# tham số -> (mã rule đo, lưới). Lưới đúng 04-01 mục G.
SWEEP_GRID: dict[str, tuple[str, tuple[float, ...]]] = {
    "FLAT_RATIO": ("FLAT_PITCH", (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)),
}


@dataclass(frozen=True)
class SweepRow:
    """Kết quả một giá trị lưới: TP/FP, P với Wilson 95 %, và recall = found/expected."""

    value: float
    tp: int
    fp: int
    precision: float | None
    ci: tuple[float, float] | None
    found: int
    expected: int
    align_fail_rate: float | None

    @property
    def recall(self) -> float | None:
        return self.found / self.expected if self.expected > 0 else None


def propose(
    rows: Sequence[SweepRow], current: float, min_precision: float = MIN_PRECISION
) -> float | None:
    """Giá trị có recall cao nhất trong các giá trị có P >= `min_precision` và n = TP+FP >= 1.

    Hoà recall thì chọn giá trị gần `current` nhất (rồi giá trị nhỏ hơn). Không có -> None (D-13).
    """
    eligible = [
        row
        for row in rows
        if row.tp + row.fp >= 1
        and row.precision is not None
        and row.precision >= min_precision - 1e-9
    ]
    if not eligible:
        return None
    best = min(
        eligible, key=lambda row: (-(row.recall or 0.0), abs(row.value - current), row.value)
    )
    return best.value


def _make_row(
    value: float, tallies: dict[str, RuleTally], code: str, align_fail_rate: float | None
) -> SweepRow:
    entry = tallies[code]
    tp, fp = entry.tp, entry.fp
    n = tp + fp
    return SweepRow(
        value=value,
        tp=tp,
        fp=fp,
        precision=tp / n if n else None,
        ci=wilson(tp, n),
        found=entry.found,
        expected=entry.expected,
        align_fail_rate=align_fail_rate,
    )


def _fmt_value(value: float) -> str:
    return f"{value:g}"


def _fmt_ratio(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


def _fmt_row(row: SweepRow, current: float) -> str:
    mark = "*" if row.value == current else ""
    ci = f"[{row.ci[0]:.2f}, {row.ci[1]:.2f}]" if row.ci is not None else "—"
    recall = f"{_fmt_ratio(row.recall)} ({row.found}/{row.expected})" if row.expected > 0 else "—"
    return (
        f"| {_fmt_value(row.value)}{mark} | {row.tp} | {row.fp} | {_fmt_ratio(row.precision)} "
        f"| {ci} | {recall} | {row.tp + row.fp} |"
    )


def _proposal_line(name: str, proposal: float | None, min_precision: float) -> str:
    if proposal is None:
        return f"Đề xuất {name}: không có giá trị đạt {min_precision * 100:g} %"
    return f"Đề xuất {name} = {_fmt_value(proposal)}"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quét ngưỡng trên tuning và đề xuất giá trị (chỉ in stdout, không ghi file)."
    )
    parser.add_argument(
        "--param",
        action="append",
        metavar="NAME",
        help="tham số cần quét (lặp được; mặc định: mọi tham số trong lưới)",
    )
    parser.add_argument("--cases", type=Path, help="cases.jsonl (mặc định: eval/cases.jsonl)")
    parser.add_argument("--data-dir", type=Path, help="DATA_DIR (mặc định: theo cấu hình app)")
    parser.add_argument(
        "--min-precision",
        type=float,
        default=MIN_PRECISION,
        help=f"biên precision tuning để được đề xuất (mặc định {MIN_PRECISION})",
    )
    return parser.parse_args(argv)


def _usage_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


@dataclass(frozen=True)
class _Subject:
    """Một đầu vào chấm lại: tính feature một lần, chấm nhiều lần ở các giá trị khác nhau."""

    score: Callable[[], ProsodyScore | None]
    observe: Callable[[ProsodyScore | None], Observation]


def _run(args: argparse.Namespace, root: Path) -> int:
    params = list(dict.fromkeys(args.param)) if args.param else list(SWEEP_GRID)
    unknown = [name for name in params if name not in SWEEP_GRID]
    if unknown:
        return _usage_error(
            f"tham số không hợp lệ: {', '.join(unknown)} (hợp lệ: {', '.join(SWEEP_GRID)})"
        )
    if not 0.0 < args.min_precision <= 1.0:
        return _usage_error("--min-precision phải nằm trong (0, 1]")

    if args.data_dir is not None:
        if not args.data_dir.is_dir():
            return _usage_error(f"--data-dir không phải thư mục: {args.data_dir}")
        os.environ["DATA_DIR"] = str(args.data_dir)
        # settings.json của app có thể ghi đè DATA_DIR; trỏ cấu hình vào chỗ trống để --data-dir
        # thắng.
        os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")

    # Import sau khi đặt biến môi trường: get_settings() phân giải DATA_DIR một lần.
    from evalkit import cases as cases_mod
    from evalkit import rescore
    from evalkit.counting import observation_from, self_observation
    from evalkit.overrides import override_thresholds

    from audio_service import config
    from audio_service.scoring import thresholds
    from audio_service.scoring.scorer import score_prosody

    config.get_settings.cache_clear()
    data_root = config.data_root()
    if not data_root.is_dir():
        return _usage_error(f"DATA_DIR không tồn tại: {data_root}")
    if root.resolve().is_relative_to(data_root):
        return _usage_error("thư mục tạm nằm trong DATA_DIR; đặt TMPDIR ra ngoài rồi chạy lại")

    cases_path = args.cases if args.cases is not None else cases_mod.CASES_PATH
    subjects: list[_Subject] = []
    try:
        every_case = cases_mod.load_cases(cases_path)
        cases_mod.validate_cases(every_case)
        tuning = cases_mod.select_split(every_case)  # D-16: không có đường nào tới held-out
        lessons = rescore.load_lessons(tuning)
        rescore.check_identity(tuning, lessons)

        clips_root = rescore.clips_root()
        ref_cache: rescore.RefCache = {}
        for case in tuning:
            if case.clip is None:
                continue
            clip = rescore.load_clip(case, lessons[case.lesson_id], clips_root, ref_cache)
            subjects.append(
                _Subject(
                    score=lambda clip=clip: rescore.score_clip(clip),
                    observe=lambda score, case=case, clip=clip: observation_from(case, clip, score),
                )
            )
        keys = [(case.lesson_id, case.segment_index, str(case.split)) for case in tuning]
        for item in rescore.self_compare_inputs(lessons, keys, root, ref_cache):
            subjects.append(
                _Subject(
                    score=lambda item=item: (
                        score_prosody(item.ref.features, item.user, item.ref.words)
                        if item.user is not None
                        else None
                    ),
                    observe=lambda score, item=item: self_observation(item, score),
                )
            )
    except (cases_mod.CaseError, rescore.DataError) as exc:
        return _usage_error(str(exc))

    for name in params:
        code, grid = SWEEP_GRID[name]
        current = getattr(thresholds, name)
        rows: list[SweepRow] = []
        for value in grid:
            with override_thresholds(**{name: value}):
                observations = [subject.observe(subject.score()) for subject in subjects]
            tallies = tally(observations)
            rows.append(_make_row(value, tallies, code, None))
        print(f"## {name} (rule {code}; hiện tại {_fmt_value(current)})")
        print("| Giá trị | TP | FP | P | CI95 | R (k/N) | n |")
        print("|---|---|---|---|---|---|---|")
        for row in rows:
            print(_fmt_row(row, current))
        print(_proposal_line(name, propose(rows, current, args.min_precision), args.min_precision))
        print()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="shadowenglab-sweep-"))
    try:
        return _run(args, root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)

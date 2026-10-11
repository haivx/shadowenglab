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
    from numpy import ndarray

    from audio_service.scoring.align import Aligner, Alignment
    from audio_service.scoring.scorer import ProsodyScore

MIN_PRECISION = 0.95  # D-13: biên 95 % ở tuning cho kỳ vọng held-out >= 90 %

# tham số -> (mã rule đo, lưới). Lưới đúng 04-01 mục G.
SWEEP_GRID: dict[str, tuple[str, tuple[float, ...]]] = {
    "STRESS_MARGIN_Z": ("STRESS_MISMATCH", (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2)),
    "PAUSE_USER_MS": ("EXTRA_PAUSE", (150, 200, 250, 300, 350, 400)),
    "PAUSE_REF_MS": ("EXTRA_PAUSE", (60, 80, 100, 120, 150)),
    "FINAL_SLOPE_MIN_ST_S": ("FINAL_CONTOUR", (3, 4, 5, 6, 7, 8, 10)),
    "FLAT_RATIO": ("FLAT_PITCH", (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)),
    "FLAT_REF_MIN_STD_ST": ("FLAT_PITCH", (1.0, 1.5, 2.0, 2.5, 3.0)),
    "PITCH_DEVIATION_ST": ("PITCH_DEVIATION", (2.0, 2.5, 3.0, 3.5, 4.0, 5.0)),
    "PD_SIGN_CONSISTENCY": ("PITCH_DEVIATION", (0.6, 0.7, 0.8, 0.9)),
    # căn thời gian (D-11b, D-17): đo gộp ba rule theo từ, vì `alignment.ok` mở/khoá chúng
    "ALIGN_COST_MAX": ("WORD_RULES", (0.90, 1.00, 1.10, 1.20, 1.30)),
}

# Mã giả WORD_RULES: ba rule chỉ chạy khi căn đáng tin (`word_issues_allowed = alignment.ok`).
WORD_RULES = ("STRESS_MISMATCH", "EXTRA_PAUSE", "PITCH_DEVIATION")

# Ghi chú cho tham số mà module khác ngoài `thresholds` và `rules.engine` cũng bind (04-01 mục G).
SHARED_NOTES = {
    "audio_service.scoring.metrics": "cũng đổi metrics.speed (điểm tổng)",
    "audio_service.scoring.align": "đổi alignment.ok cho mọi rule theo từ",
    "audio_service.scoring.prominence": (
        "cũng đổi prominence.pause_entries (mục pauses, không vào điểm tổng)"
    ),
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


def make_row(
    value: float, tallies: dict[str, RuleTally], code: str, align_fail_rate: float | None
) -> SweepRow:
    """Dòng của một giá trị: lấy tally của `code`, hoặc cộng ba rule theo từ khi `WORD_RULES`."""
    entries = [tallies[name] for name in (WORD_RULES if code == "WORD_RULES" else (code,))]
    tp = sum(entry.tp for entry in entries)
    fp = sum(entry.fp for entry in entries)
    n = tp + fp
    return SweepRow(
        value=value,
        tp=tp,
        fp=fp,
        precision=tp / n if n else None,
        ci=wilson(tp, n),
        found=sum(entry.found for entry in entries),
        expected=sum(entry.expected for entry in entries),
        align_fail_rate=align_fail_rate,
    )


def align_fail_rate(observations: Sequence[Observation]) -> float | None:
    """Tỉ lệ căn không đáng tin (`alignment.ok` = False) trong các lần chấm có tiếng (D-11b)."""
    voiced = [obs for obs in observations if obs.voiced]
    if not voiced:
        return None
    return sum(1 for obs in voiced if not obs.align_ok) / len(voiced)


def _fmt_value(value: float) -> str:
    return f"{value:g}"


def _fmt_ratio(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "—"


def _fmt_row(row: SweepRow, current: float, *, show_align: bool = False) -> str:
    mark = "*" if row.value == current else ""
    ci = f"[{row.ci[0]:.2f}, {row.ci[1]:.2f}]" if row.ci is not None else "—"
    recall = f"{_fmt_ratio(row.recall)} ({row.found}/{row.expected})" if row.expected > 0 else "—"
    line = (
        f"| {_fmt_value(row.value)}{mark} | {row.tp} | {row.fp} | {_fmt_ratio(row.precision)} "
        f"| {ci} | {recall} | {row.tp + row.fp} |"
    )
    if not show_align:
        return line
    rate = f"{row.align_fail_rate * 100:.0f} %" if row.align_fail_rate is not None else "—"
    return f"{line} {rate} |"


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

    score: Callable[[Aligner], ProsodyScore | None]
    observe: Callable[[ProsodyScore | None], Observation]
    mfccs: tuple[ndarray, ndarray] | None  # (bản gốc, người học) để căn; None = không có tiếng


def _fixed_aligner(alignment: Alignment) -> Aligner:
    """Aligner trả lại một Alignment đã tính: tham số không phải ALIGN_* không đổi phép căn."""

    def aligner(ref_mfcc: ndarray, user_mfcc: ndarray) -> Alignment:
        return alignment

    return aligner


def _header(name: str, code: str, current: float, notes: Sequence[str]) -> str:
    shown = "+".join(WORD_RULES) + " gộp" if code == "WORD_RULES" else code
    line = f"## {name} (rule {shown}; hiện tại {_fmt_value(current)})"
    return f"{line} — {'; '.join(notes)}" if notes else line


# Hai module luôn bind mọi ngưỡng: không cần ghi chú.
_QUIET_MODULES = ("audio_service.scoring.thresholds", "audio_service.rules.engine")


def _notes(name: str) -> list[str]:
    """Ghi chú cho module ngoài `thresholds` và `rules.engine` cũng bind `name`."""
    from evalkit.overrides import bound_in

    return [
        SHARED_NOTES.get(module, f"cũng đổi {module}")
        for module in bound_in(name)
        if module in SHARED_NOTES or module not in _QUIET_MODULES
    ]


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
    from audio_service.scoring import align as align_module
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
                    score=lambda aligner, clip=clip: rescore.score_clip(clip, aligner=aligner),
                    observe=lambda score, case=case, clip=clip: observation_from(case, clip, score),
                    mfccs=(clip.ref.features.mfcc, clip.user.mfcc)
                    if clip.user is not None
                    else None,
                )
            )
        keys = [(case.lesson_id, case.segment_index, str(case.split)) for case in tuning]
        for item in rescore.self_compare_inputs(lessons, keys, root, ref_cache):
            subjects.append(
                _Subject(
                    score=lambda aligner, item=item: (
                        score_prosody(item.ref.features, item.user, item.ref.words, aligner=aligner)
                        if item.user is not None
                        else None
                    ),
                    observe=lambda score, item=item: self_observation(item, score),
                    mfccs=(item.ref.features.mfcc, item.user.mfcc)
                    if item.user is not None
                    else None,
                )
            )
    except (cases_mod.CaseError, rescore.DataError) as exc:
        return _usage_error(str(exc))

    # Căn tính một lần ở giá trị hiện tại, dùng lại cho mọi tham số không phải ALIGN_*.
    fixed: dict[int, Aligner] = {}
    summary: list[str] = []
    for name in params:
        code, grid = SWEEP_GRID[name]
        current = getattr(thresholds, name)
        sweeps_alignment = name.startswith("ALIGN_")
        if not sweeps_alignment and not fixed:
            fixed = {
                position: _fixed_aligner(align_module.align(*subject.mfccs))
                for position, subject in enumerate(subjects)
                if subject.mfccs is not None
            }
        rows: list[SweepRow] = []
        for value in grid:
            with override_thresholds(**{name: value}):
                observations = [
                    subject.observe(
                        subject.score(
                            align_module.align
                            if sweeps_alignment
                            else fixed.get(position, align_module.align)
                        )
                    )
                    for position, subject in enumerate(subjects)
                ]
            rows.append(make_row(value, tally(observations), code, align_fail_rate(observations)))
        proposal = propose(rows, current, args.min_precision)
        print(_header(name, code, current, _notes(name)))
        print(
            "| Giá trị | TP | FP | P | CI95 | R (k/N) | n |"
            + (" Căn thất bại |" if sweeps_alignment else "")
        )
        print("|---|---|---|---|---|---|---|" + ("---|" if sweeps_alignment else ""))
        for row in rows:
            print(_fmt_row(row, current, show_align=sweeps_alignment))
        print(_proposal_line(name, proposal, args.min_precision))
        print()
        summary.append(
            f"- {name}: "
            + (
                f"{_fmt_value(proposal)} (hiện tại {_fmt_value(current)})"
                if proposal is not None
                else f"không có giá trị đạt {args.min_precision * 100:g} %"
            )
        )
    print("## Tóm tắt đề xuất")
    print("\n".join(summary))
    print("Sweep chỉ in bảng; Liam chọn giá trị và tự sửa thresholds.py (D-13).")
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

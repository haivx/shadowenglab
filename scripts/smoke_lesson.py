"""Smoke test pipeline tạo bài đầu-cuối trên một video YouTube thật (P0, FND-07).

    uv run --project services/audio --frozen python scripts/smoke_lesson.py <url> \
        [--start S] [--end E] [--budget-s N]

In `LESSON_ID=<ulid>`, bảng thời gian từng bước, rồi tự kiểm tra lesson.json + feature và in
`SELF-CHECK OK`. Với --budget-s in `BUDGET OK` hoặc `BUDGET EXCEEDED` (thoát 3).
Thoát 2: URL hoặc khoảng sai. Thoát 1: pipeline lỗi.
"""

from __future__ import annotations

import argparse
import sys
import time

import numpy as np

# isort: split
from audio_service.config import lesson_dir, lesson_json_path, segment_features_path
from audio_service.contract_io import write_json_atomic
from audio_service.contracts_gen import Lesson
from audio_service.lesson.pipeline import run_lesson
from audio_service.lesson.timing import StepTimer, format_timing_table
from audio_service.lesson.urls import InvalidYoutubeUrl

NPZ_KEYS = ("f0_hz", "energy", "ppg", "window")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy pipeline tạo bài trên một video YouTube.")
    parser.add_argument("url", help="link video YouTube")
    parser.add_argument("--start", type=float, default=None, help="giây bắt đầu (mặc định 0)")
    parser.add_argument(
        "--end", type=float, default=None, help="giây kết thúc (mặc định hết video)"
    )
    parser.add_argument(
        "--budget-s",
        type=float,
        default=None,
        help="tổng thời gian tối đa (giây); vượt thì thoát 3",
    )
    return parser.parse_args(argv)


def _self_check(lesson_id: str) -> Lesson:
    """Đọc lại lesson.json bằng model sinh từ contract và kiểm từng segment có đủ feature."""
    lesson = Lesson.model_validate_json(lesson_json_path(lesson_id).read_text(encoding="utf-8"))
    assert lesson.status == "ready", f"status là {lesson.status}, cần ready"
    assert len(lesson.segments) >= 1, "không có segment nào"
    for seg in lesson.segments:
        with np.load(segment_features_path(lesson_id, seg.index)) as npz:
            missing = [key for key in NPZ_KEYS if key not in npz.files]
            assert not missing, f"segment {seg.index} thiếu {missing}"
    return lesson


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    timer = StepTimer()
    last: list[Lesson] = []

    def on_status(lesson: Lesson) -> None:
        if not last:
            print(f"LESSON_ID={lesson.id}", flush=True)
        last.append(lesson)
        print(f"  [{lesson.status}]", flush=True)

    t0 = time.perf_counter()
    try:
        run = run_lesson(args.url, start=args.start, end=args.end, timer=timer, on_status=on_status)
    except (InvalidYoutubeUrl, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except BaseException as exc:  # noqa: BLE001 - mọi lỗi pipeline đều phải in step + message
        if isinstance(exc, KeyboardInterrupt):
            raise
        failed = last[-1] if last else None
        step = failed.error.step if failed and failed.error else "?"
        message = (
            failed.error.message if failed and failed.error else f"{type(exc).__name__}: {exc}"
        )
        print(f"PIPELINE FAILED at step '{step}': {message}", file=sys.stderr)
        return 1
    wall = time.perf_counter() - t0

    lesson = run.lesson
    range_dur = lesson.range.end - lesson.range.start
    quality = lesson.audio_quality
    db = 10 * np.log10(max(run.non_vocal_ratio, 1e-12))
    label = quality.label if quality else "?"
    extras = {
        "lesson": str(run.lesson_path),
        "range": f"{lesson.range.start:.1f}-{lesson.range.end:.1f} s ({range_dur:.1f} s)",
        "wall time": f"{wall:.1f} s",
        "realtime factor": f"{wall / range_dur:.2f}x",
        "nonVocalRatio": f"{run.non_vocal_ratio:.3e} ({db:.1f} dB) -> {label}",
        "segments": str(len(lesson.segments)),
    }
    print()
    print(format_timing_table(run.timings, extras))

    write_json_atomic(
        lesson_dir(lesson.id) / "timing.json",
        {
            "timings": run.timings,
            "total": timer.total(),
            "wallSec": round(wall, 2),
            "extras": extras,
        },
    )

    try:
        _self_check(lesson.id)
    except (AssertionError, OSError, ValueError) as exc:
        print(f"SELF-CHECK FAILED: {exc}", file=sys.stderr)
        return 1
    print("SELF-CHECK OK")

    if args.budget_s is not None:
        if wall > args.budget_s:
            print(f"BUDGET EXCEEDED: {wall:.1f} s > {args.budget_s:.1f} s")
            return 3
        print(f"BUDGET OK: {wall:.1f} s <= {args.budget_s:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

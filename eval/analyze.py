"""Chấm lại bộ eval nội bộ và sinh `eval/report.md` (Phase 4, EVL-02).

    uv run --project services/audio --frozen python eval/analyze.py \
        [--cases eval/cases.jsonl] [--report eval/report.md] [--data-dir PATH]

(`make eval` gọi đúng lệnh này.) Nạp `eval/cases.jsonl` bằng pydantic `EvalCase`, chấm lại từng WAV
đã lưu trong `DATA_DIR/eval_clips` bằng scorer HIỆN TẠI (D-06: gọi hàm Python, không HTTP, không đọc
`result_json` cũ), đếm TP/FP theo bảng D-10 đã duyệt ở 04-01 rồi ghi bảng rule x P/R/n/CI Wilson
95 % (D-14, D-20).

Chỉ case `split = tuning` được nạp và chấm; WAV của case held-out không bao giờ được đọc ở đây
(D-16). Case thiếu `split` làm script thoát 2 (D-12).

Thoát 0 và in `EVAL OK` ở dòng cuối. Thoát 2: tham số sai, thiếu file, case sai bất biến, lệch dấu
nhận diện câu (D-05), bài không còn, thiếu WAV hoặc sidecar không khớp; khi đó `report.md` không bị
ghi đè (ghi `.part` rồi `os.replace`, chỉ sau khi mọi bước thành công).

CHỈ ĐỌC DATA_DIR (T-04-04): `ref_prosody_for_segment(..., write_cache=False)`, không `mkdir`, không
SQLite; file tạm nằm trong thư mục tạm của hệ thống và bị xoá trong `finally`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chấm lại bộ eval tuning và sinh eval/report.md, chỉ đọc DATA_DIR."
    )
    parser.add_argument("--cases", type=Path, help="cases.jsonl (mặc định: eval/cases.jsonl)")
    parser.add_argument("--report", type=Path, help="report.md (mặc định: eval/report.md)")
    parser.add_argument("--data-dir", type=Path, help="DATA_DIR (mặc định: theo cấu hình app)")
    return parser.parse_args(argv)


def _usage_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def write_report(path: Path, text: str) -> None:
    """Ghi `path` atomic: vào `<tên>.part` rồi `os.replace` (không để report ghi dở, T-04-06)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        part.write_text(text, encoding="utf-8")
        os.replace(part, path)
    finally:
        part.unlink(missing_ok=True)


def _run(args: argparse.Namespace, root: Path) -> int:
    if args.data_dir is not None:
        if not args.data_dir.is_dir():
            return _usage_error(f"--data-dir không phải thư mục: {args.data_dir}")
        os.environ["DATA_DIR"] = str(args.data_dir)
        # settings.json của app có thể ghi đè DATA_DIR; trỏ cấu hình vào chỗ trống để --data-dir
        # thắng.
        os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")

    # Import sau khi đặt biến môi trường: get_settings() phân giải DATA_DIR một lần.
    from evalkit import cases as cases_mod
    from evalkit import counting, rescore
    from evalkit import report as report_mod

    from audio_service import config
    from audio_service.scoring.features import FEAT_VERSION
    from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION

    config.get_settings.cache_clear()
    data_root = config.data_root()
    if not data_root.is_dir():
        return _usage_error(f"DATA_DIR không tồn tại: {data_root}")
    if root.resolve().is_relative_to(data_root):
        return _usage_error("thư mục tạm nằm trong DATA_DIR; đặt TMPDIR ra ngoài rồi chạy lại")

    cases_path = args.cases if args.cases is not None else cases_mod.CASES_PATH
    report_path = (
        args.report if args.report is not None else config.REPO_ROOT / "eval" / "report.md"
    )

    try:
        every_case = cases_mod.load_cases(cases_path)
        cases_mod.validate_cases(every_case)
        tuning = cases_mod.select_split(every_case)
        lessons = rescore.load_lessons(tuning)
        rescore.check_identity(tuning, lessons)

        clips_root = rescore.clips_root()
        ref_cache: rescore.RefCache = {}
        observations: list[counting.Observation] = []
        untagged = 0
        for case in tuning:
            if case.clip is None:
                untagged += 1
                continue
            clip = rescore.load_clip(case, lessons[case.lesson_id], clips_root, ref_cache)
            observations.append(counting.observation_from(case, clip, rescore.score_clip(clip)))
    except (cases_mod.CaseError, rescore.DataError) as exc:
        return _usage_error(str(exc))

    tallies = counting.tally(observations)
    info = report_mod.RunInfo(
        mode="tuning",
        thresholds_version=THRESHOLDS_VERSION,
        scorer_version=SCORER_VERSION,
        feat_version=FEAT_VERSION,
        git_sha=report_mod.git_sha(config.REPO_ROOT),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        n_cases=len(every_case),
        n_scored=len(observations),
        n_untagged=untagged,
    )
    scored_ids = {obs.case_id for obs in observations if obs.case_id is not None}
    text = report_mod.render_report(
        info,
        tallies,
        fps=counting.fp_rows(observations),
        failures=counting.align_failures(observations),
        coverage=counting.coverage_rows(every_case, scored_ids),
    )
    write_report(report_path, text)

    pooled = tallies[counting.POOLED]
    print(
        f"{len(observations)} clip tuning đã chấm, {untagged} case chưa gắn clip; "
        f"TP {pooled.tp}, FP {pooled.fp}"
    )
    print("EVAL OK")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="shadowenglab-eval-"))
    try:
        return _run(args, root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)

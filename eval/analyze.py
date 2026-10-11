"""Chấm lại bộ eval nội bộ và sinh `eval/report.md` (Phase 4, EVL-02).

    uv run --project services/audio --frozen python eval/analyze.py \
        [--cases eval/cases.jsonl] [--report eval/report.md] [--data-dir PATH]

(`make eval` gọi đúng lệnh này.) Nạp `eval/cases.jsonl` bằng pydantic `EvalCase`, chấm lại từng WAV
đã lưu trong `DATA_DIR/eval_clips` bằng scorer HIỆN TẠI (D-06: gọi hàm Python, không HTTP, không đọc
`result_json` cũ), đếm TP/FP theo bảng D-10 đã duyệt ở 04-01 rồi ghi bảng rule x P/R/n/CI Wilson
95 % (D-14, D-20).

Chỉ case `split = tuning` được nạp và chấm; WAV của case held-out không bao giờ được đọc ở đây
(D-16). Case thiếu `split` làm script thoát 2 (D-12).

Thoát 0 và in `EVAL OK` ở dòng cuối (kèm cảnh báo khi mốc tự so có issue). Thoát 1 chỉ khi chạy có
held-out và `verdict` thấy rule đang bật FAIL hoặc mốc tự so có issue (D-21; chưa nối ở plan này,
chạy hiện chỉ tuning). Thoát 2: tham số sai, thiếu file, case sai bất biến, lệch dấu
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
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from evalkit.counting import (
    LAYER_C_CODES,
    PRECISION_BAR,
    STATUS_FAIL,
    RuleTally,
    SelfRow,
    rule_status,
)

OK = "EVAL OK"
FAILED = "EVAL FAILED: "


def verdict(
    tallies_by_split: Mapping[str, Mapping[str, RuleTally]],
    self_rows: Sequence[SelfRow],
    enabled: Sequence[str],
    *,
    holdout_included: bool,
) -> tuple[str, int]:
    """Kết luận của gate và mã thoát (04-01 F3, D-21). Hàm thuần: số liệu vào, (message, code) ra.

    Chỉ khi chạy có held-out mới trả 1, và chỉ khi có rule ĐANG BẬT `FAIL` trên held-out (P < 0.90
    với n >= 1; `CHƯA ĐỦ MẪU` và `TẮT` không phải lý do) hoặc mốc tự so có issue (D-18a). Nhiều
    lý do nối bằng "; ". Chạy chỉ tuning luôn trả 0; mốc tự so có issue thì message vẫn bắt đầu
    `EVAL OK` nhưng kèm cảnh báo.
    """
    self_problems = [
        f"mốc tự so có issue ở bài {row.lesson_id} câu {row.segment_index} "
        f"({', '.join(row.codes) if row.codes else row.n_issues})"
        for row in self_rows
        if row.n_issues > 0
    ]
    if not holdout_included:
        if self_problems:
            return f"{OK} (cảnh báo: {'; '.join(self_problems)})", 0
        return OK, 0
    held = tallies_by_split.get("heldout", {})
    problems: list[str] = []
    for code in LAYER_C_CODES:
        if code not in enabled:
            continue
        tally = held.get(code, RuleTally())
        if rule_status(tally, True) == STATUS_FAIL:
            n = tally.tp + tally.fp
            problems.append(
                f"{code} precision held-out {tally.tp / n:.2f} (n={n}) < {PRECISION_BAR:.2f}"
            )
    problems.extend(self_problems)
    if problems:
        return FAILED + "; ".join(problems), 1
    return OK, 0


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
    from audio_service.rules.engine import enabled_codes
    from audio_service.scoring.features import FEAT_VERSION
    from audio_service.scoring.scorer import score_prosody
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
        n_clips = len(observations)

        # Mốc tự so (D-18a): mọi câu có case trong tập đang chấm, kể cả case chưa gắn clip.
        keys = [(case.lesson_id, case.segment_index, str(case.split)) for case in tuning]
        for item in rescore.self_compare_inputs(lessons, keys, root, ref_cache):
            score = None
            if item.user is not None:
                score = score_prosody(item.ref.features, item.user, item.ref.words)
            observations.append(counting.self_observation(item, score))
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
        n_scored=n_clips,
        n_untagged=untagged,
    )
    scored_ids = {obs.case_id for obs in observations if obs.case_id is not None}
    enabled = enabled_codes()
    self_compare = counting.self_rows(observations)
    # Held-out chưa được nạp ở đây (04-06 nối `--holdout`): gate chạy ở chế độ chỉ tuning.
    message, exit_code = verdict({"tuning": tallies}, self_compare, enabled, holdout_included=False)
    text = report_mod.render_report(
        info,
        tallies,
        fps=counting.fp_rows(observations),
        failures=counting.align_failures(observations),
        coverage=counting.coverage_rows(every_case, scored_ids),
        self_compare=self_compare,
        enabled=enabled,
    )
    write_report(report_path, text)

    total = counting.pooled(tallies, enabled)
    print(
        f"{n_clips} clip tuning đã chấm, {untagged} case chưa gắn clip, "
        f"{len(observations) - n_clips} câu tự so; TP {total.tp}, FP {total.fp}"
    )
    print(message)
    return exit_code


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

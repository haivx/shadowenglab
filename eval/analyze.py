"""Chấm lại bộ eval nội bộ và sinh `eval/report.md` (Phase 4, EVL-02).

    uv run --project services/audio --frozen python eval/analyze.py \
        [--cases eval/cases.jsonl] [--report eval/report.md] [--data-dir PATH] \
        [--holdout [--holdout-log eval/holdout_log.jsonl]]

(`make eval` gọi lệnh này; `make eval HOLDOUT=1` thêm `--holdout`.) Nạp `eval/cases.jsonl` bằng
pydantic `EvalCase`, chấm lại từng WAV đã lưu trong `DATA_DIR/eval_clips` bằng scorer HIỆN TẠI
(D-06: gọi hàm Python, không HTTP, không đọc `result_json` cũ), đếm TP/FP theo bảng D-10 đã duyệt ở
04-01 rồi ghi bảng rule x P/R/n/CI Wilson 95 % (D-14, D-20).

Mặc định chỉ case `split = tuning` được nạp và chấm; WAV của case held-out không được đọc và
`holdout_log.jsonl` không bị chạm (D-16). Chỉ `--holdout` mới chấm cả held-out: mỗi lần chấm xong
(mã 0 hoặc 1) thêm đúng một dòng log rồi mới ghi report (report in cả log), và nhãn held-out phải
còn nguyên so với dòng log đầu (D-09). Case thiếu `split` làm script thoát 2 (D-12).

Thoát 0 và in `EVAL OK` ở dòng cuối (kèm cảnh báo khi mốc tự so có issue). Thoát 1 chỉ khi chạy có
held-out và `verdict` thấy rule đang bật FAIL hoặc mốc tự so có issue (D-21). Thoát 2: tham số sai,
thiếu file, case sai bất biến, lệch dấu nhận diện câu (D-05), bài không còn, thiếu WAV, sidecar
không khớp hoặc log held-out hỏng; khi đó `report.md` không bị ghi đè (ghi `.part` rồi
`os.replace`, chỉ sau khi mọi bước thành công) và log không thêm dòng.

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
from typing import Any

from evalkit.counting import (
    LAYER_C_CODES,
    PRECISION_BAR,
    STATUS_FAIL,
    RuleTally,
    SelfRow,
    rule_status,
)
from evalkit.stats import (
    DETERMINISM_SAMPLE,
    Determinism,
    ScoredClip,
    build_retest,
    scores_equal,
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
    parser.add_argument(
        "--holdout",
        action="store_true",
        help="mở và chấm held-out (D-16): thêm một dòng vào holdout_log.jsonl, áp gate D-21",
    )
    parser.add_argument(
        "--holdout-log",
        type=Path,
        help="holdout_log.jsonl (mặc định: eval/holdout_log.jsonl)",
    )
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


def check_determinism(
    scored: Sequence[ScoredClip],
    lessons: Mapping[str, Any],
    clips_root: Path,
    rescore: Any,
) -> Determinism:
    """Chấm lại `DETERMINISM_SAMPLE` clip đầu (theo caseId) lần hai từ đầu (D-19, T-04-17).

    Nạp lại bằng `load_clip` với `ref_cache` mới nên feature bản gốc cũng được tính lại. Overall
    phải bằng nhau tuyệt đối và issues bằng nhau theo JSON chuẩn hoá; lệch thì ghi caseId.
    """
    sample = sorted(scored, key=lambda item: item.case.case_id)[:DETERMINISM_SAMPLE]
    failed: list[str] = []
    for item in sample:
        clip = rescore.load_clip(item.case, lessons[item.case.lesson_id], clips_root, {})
        if not scores_equal(item.score, rescore.score_clip(clip)):
            failed.append(item.case.case_id)
    return Determinism(len(sample), tuple(failed))


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
    from evalkit import holdout as holdout_mod
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
    log_path = args.holdout_log if args.holdout_log is not None else holdout_mod.HOLDOUT_LOG_PATH
    opened = args.holdout

    try:
        every_case = cases_mod.load_cases(cases_path)
        cases_mod.validate_cases(every_case)
        added_later: list[str] = []
        if opened:
            # Log hỏng (T-04-16) hoặc nhãn đã đóng băng bị đổi (T-04-14, D-09): thoát 2 TRƯỚC khi
            # chấm, không ghi log, không ghi report.
            added_later = holdout_mod.check_frozen(every_case, holdout_mod.read_log(log_path))
        scoring = cases_mod.select_split(every_case, include_heldout=opened)
        lessons = rescore.load_lessons(scoring)
        rescore.check_identity(scoring, lessons)

        clips_root = rescore.clips_root()
        ref_cache: rescore.RefCache = {}
        observations: list[counting.Observation] = []
        scored: list[ScoredClip] = []
        untagged = 0
        for case in scoring:
            if case.clip is None:
                untagged += 1
                continue
            clip = rescore.load_clip(case, lessons[case.lesson_id], clips_root, ref_cache)
            score = rescore.score_clip(clip)
            scored.append(ScoredClip(case, score))
            observations.append(counting.observation_from(case, clip, score))
        n_clips = len(observations)
        determinism = check_determinism(scored, lessons, clips_root, rescore)

        # Mốc tự so (D-18a): mọi câu có case trong tập đang chấm, kể cả case chưa gắn clip.
        keys = [(case.lesson_id, case.segment_index, str(case.split)) for case in scoring]
        for item in rescore.self_compare_inputs(lessons, keys, root, ref_cache):
            score = None
            if item.user is not None:
                score = score_prosody(item.ref.features, item.user, item.ref.words)
            observations.append(counting.self_observation(item, score))
    except (
        cases_mod.CaseError,
        rescore.DataError,
        holdout_mod.HoldoutLogError,
        holdout_mod.HoldoutViolation,
    ) as exc:
        return _usage_error(str(exc))

    by_split = {
        side: counting.tally([obs for obs in observations if obs.split == side])
        for side in (("tuning", "heldout") if opened else ("tuning",))
    }
    tallies = by_split["tuning"]
    generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    git_sha = report_mod.git_sha(config.REPO_ROOT)
    enabled = enabled_codes()
    self_compare = counting.self_rows(observations)
    message, exit_code = verdict(by_split, self_compare, enabled, holdout_included=opened)
    retest = build_retest(scored)
    if not determinism.ok:
        # Chỉ cảnh báo, không đổi mã thoát (04-01 J, D-21 không liệt kê kiểm tất định).
        print(
            "cảnh báo: kiểm tất định FAIL, chấm lại cho kết quả khác ở "
            + ", ".join(determinism.failed),
            file=sys.stderr,
        )

    log_entries: list[holdout_mod.HoldoutEntry] | None = None
    if opened:
        # Ghi log TRƯỚC report để report in cả dòng vừa thêm (D-16); lỗi dữ liệu đã thoát 2 ở trên.
        entry = holdout_mod.make_entry(every_case, opened_at=generated_at, git_sha=git_sha)
        try:
            holdout_mod.append_entry(log_path, entry)
            log_entries = holdout_mod.read_log(log_path)
        except (OSError, holdout_mod.HoldoutLogError) as exc:
            return _usage_error(f"không ghi được {log_path.name}: {type(exc).__name__}")
    mode = (
        f"tuning + held-out (lần mở thứ {len(log_entries)})"
        if log_entries is not None
        else "tuning (held-out khoá, D-16)"
    )
    info = report_mod.RunInfo(
        mode=mode,
        thresholds_version=THRESHOLDS_VERSION,
        scorer_version=SCORER_VERSION,
        feat_version=FEAT_VERSION,
        git_sha=git_sha,
        generated_at=generated_at,
        n_cases=len(every_case),
        n_scored=n_clips,
        n_untagged=untagged,
    )
    scored_ids = {obs.case_id for obs in observations if obs.case_id is not None}
    text = report_mod.render_report(
        info,
        tallies,
        fps=counting.fp_rows(observations),
        failures=counting.align_failures(observations),
        coverage=counting.coverage_rows(every_case, scored_ids),
        self_compare=self_compare,
        enabled=enabled,
        heldout=by_split.get("heldout"),
        gate_message=message if opened else None,
        holdout_log=log_entries,
        added_after_first=added_later if opened else None,
        retest=retest,
        determinism=determinism,
    )
    write_report(report_path, text)

    total = counting.pooled(counting.tally(observations), enabled)
    names = "tuning + held-out" if opened else "tuning"
    print(
        f"{n_clips} clip {names} đã chấm, {untagged} case chưa gắn clip, "
        f"{len(observations) - n_clips} câu tự so; TP {total.tp}, FP {total.fp}"
    )
    if not opened:
        times = holdout_mod.count_openings(log_path)
        if times:
            print(f"held-out đã mở {times} lần (log: {log_path.name}); lần này giữ khoá")
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

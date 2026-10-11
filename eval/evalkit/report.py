"""Dựng `eval/report.md` (04-02, D-14, D-20). Chỉ số liệu, ID và chữ của từ; không audio, không
đường dẫn tuyệt đối (T-04-05).

`render_report` là hàm thuần (chuỗi ra); `git_sha` là chỗ duy nhất gọi git. Mọi con số trong report
phải do một lần chạy analyze tạo ra ở đúng git sha và versions ghi ở đầu file (minh bạch eval).
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from evalkit.counting import (
    LAYER_C_CODES,
    POOLED,
    CoverageRow,
    FpRow,
    RuleTally,
    SelfRow,
    wilson,
)

HELDOUT_LOCKED = "khoá (D-16)"
RULE_OFF = "TẮT (D-15)"
GIT_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class RunInfo:
    """Định danh một lần chạy: chế độ, versions, git, số case."""

    mode: str
    thresholds_version: str
    scorer_version: str
    feat_version: str
    git_sha: str
    generated_at: str
    n_cases: int
    n_scored: int
    n_untagged: int


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


def git_sha(repo_root: Path) -> str:
    """12 ký tự đầu của HEAD, thêm `-dirty` khi cây có thay đổi; `unknown` nếu không có git."""
    sha = _git(repo_root, "rev-parse", "--short=12", "HEAD")
    if not sha:
        return "unknown"
    status = _git(repo_root, "status", "--porcelain")
    return f"{sha}-dirty" if status else sha


def _precision_cell(tally: RuleTally) -> str:
    n = tally.tp + tally.fp
    interval = wilson(tally.tp, n)
    if interval is None:
        return "— (n=0)"
    return f"{tally.tp / n:.2f} [{interval[0]:.2f}, {interval[1]:.2f}] (n={n})"


def _recall_cell(tally: RuleTally) -> str:
    interval = wilson(tally.found, tally.expected)
    if interval is None:
        return "— (0/0)"
    rate = tally.found / tally.expected
    span = f"[{interval[0]:.2f}, {interval[1]:.2f}]"
    return f"{rate:.2f} ({tally.found}/{tally.expected}) {span}"


def _cell(text: object) -> str:
    """Một ô bảng markdown: không xuống dòng, không dấu `|`."""
    return str(text).replace("|", "/").replace("\n", " ")


def _summary_table(tallies: Mapping[str, RuleTally], enabled: Sequence[str]) -> list[str]:
    lines = [
        "| Rule | TP | FP | Tuning P [CI95] (n) | Tuning R (k/N) [CI95] | Held-out |",
        "|---|---|---|---|---|---|",
    ]
    for code in (*LAYER_C_CODES, POOLED):
        if code in LAYER_C_CODES and code not in enabled:
            lines.append(f"| {code} | " + " | ".join([RULE_OFF] * 5) + " |")
            continue
        row = tallies.get(code, RuleTally())
        lines.append(
            f"| {code} | {row.tp} | {row.fp} | {_precision_cell(row)} | "
            f"{_recall_cell(row)} | {HELDOUT_LOCKED} |"
        )
    return lines


def _fp_section(fps: Sequence[FpRow]) -> list[str]:
    lines = [
        "## Danh sách FP",
        "",
        "Nghe lại từng dòng; nếu lỗi có thật, ghi `alsoPresent` cho case "
        "(chỉ clip tuning hoặc trước lần mở held-out đầu, D-09).",
        "",
    ]
    if not fps:
        return [*lines, "Không có FP.", ""]
    lines += [
        "| split | caseId | clip | khai báo | mã issue | wordIndex | từ |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in fps:
        at = "—" if row.word_index is None else row.word_index
        text = row.word_text if row.word_text is not None else "—"
        lines.append(
            f"| {_cell(row.split)} | {_cell(row.case_id)} | {_cell(row.clip)} | "
            f"{_cell(row.declared)} | {row.code} | {at} | {_cell(text)} |"
        )
    return [*lines, ""]


def _failure_section(failures: Mapping[tuple[str, str], tuple[int, int]]) -> list[str]:
    lines = [
        "## Tỉ lệ căn thất bại (D-11b)",
        "",
        "Căn thời gian không đạt (`alignment.ok` sai, hoặc clip không có tiếng) làm rule theo từ "
        "không chạy: case lỗi theo từ thành FN. Theo bài x errorType.",
        "",
    ]
    if not failures:
        return [*lines, "Chưa có clip nào được chấm.", ""]
    lines += ["| bài | errorType | thất bại/tổng | % |", "|---|---|---|---|"]
    for (lesson_id, label), (failed, total) in sorted(failures.items()):
        lines.append(
            f"| {_cell(lesson_id)} | {_cell(label)} | {failed}/{total} | "
            f"{100.0 * failed / total:.0f} % |"
        )
    return [*lines, ""]


def _self_section(rows: Sequence[SelfRow]) -> list[str]:
    lines = [
        "## Mốc tự so (D-18a)",
        "",
        "Mỗi câu có case: lát vocal của chính bản gốc, đệm lặng, mã hoá webm/opus rồi chuẩn hoá "
        "như một lượt tải lên. Mọi issue ở đây là FP.",
        "",
    ]
    if not rows:
        return [*lines, "Chưa có câu nào.", ""]
    overalls = sorted(row.overall for row in rows)
    middle = len(overalls) // 2
    median = (
        overalls[middle] if len(overalls) % 2 else (overalls[middle - 1] + overalls[middle]) / 2
    )
    lines += [
        f"tự so: {len(rows)} câu, trung vị overall {median:.3f}, "
        f"tổng issue {sum(row.n_issues for row in rows)}",
        "",
        "| bài | câu | split | overall | số issue | mã issue |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        overall = f"{row.overall:.3f}" if row.voiced else "không có tiếng"
        codes = ", ".join(row.codes) if row.codes else "—"
        lines.append(
            f"| {_cell(row.lesson_id)} | {row.segment_index} | {_cell(row.split)} | "
            f"{overall} | {row.n_issues} | {codes} |"
        )
    return [*lines, ""]


def _coverage_section(coverage: Sequence[CoverageRow]) -> list[str]:
    lines = ["## Phủ", "", "Số case theo errorType x split (held-out chỉ đếm, không chấm).", ""]
    if not coverage:
        return [*lines, "Chưa có case nào.", ""]
    lines += [
        "| errorType | split | tổng | đã gắn clip | đã chấm |",
        "|---|---|---|---|---|",
    ]
    for row in coverage:
        lines.append(
            f"| {_cell(row.label)} | {_cell(row.split)} | {row.total} | {row.tagged} | "
            f"{row.scored} |"
        )
    return [*lines, ""]


def render_report(
    info: RunInfo,
    tallies: Mapping[str, RuleTally],
    *,
    fps: Sequence[FpRow] = (),
    failures: Mapping[tuple[str, str], tuple[int, int]] | None = None,
    coverage: Sequence[CoverageRow] = (),
    self_compare: Sequence[SelfRow] = (),
    enabled: Sequence[str] | None = None,
) -> str:
    """Nội dung `report.md`: versions/git/chế độ, bảng rule x P/R/n/CI Wilson, FP, căn, phủ.

    `enabled`: mã các rule đang bật; mặc định `enabled_codes()` của engine (D-15). Rule tắt hiện
    `TẮT (D-15)` thay cho số.
    """
    if enabled is None:
        from audio_service.rules.engine import enabled_codes

        enabled = enabled_codes()
    lines = [
        "# Báo cáo eval nội bộ (Phase 4)",
        "",
        f"- Chế độ: {info.mode} (held-out khoá, D-16)",
        f"- THRESHOLDS_VERSION `{info.thresholds_version}` · SCORER_VERSION "
        f"`{info.scorer_version}` · FEAT_VERSION `{info.feat_version}`",
        f"- Git: `{info.git_sha}` · sinh lúc {info.generated_at}",
        f"- Case: {info.n_cases} trong file; tuning đã chấm {info.n_scored}, "
        f"chưa gắn clip {info.n_untagged}",
        "",
        "## Tóm tắt theo rule (tuning)",
        "",
        "P = TP / (TP + FP); R = số case có TP / số case có mã chính này; "
        "khoảng tin cậy Wilson 95 %.",
        "",
        *_summary_table(tallies, enabled),
        "",
        *_fp_section(fps),
        *_failure_section(failures or {}),
        *_self_section(self_compare),
        *_coverage_section(coverage),
    ]
    return "\n".join(lines)

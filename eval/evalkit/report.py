"""Dựng `eval/report.md` (04-02, D-14, D-20). Chỉ số liệu, ID và chữ của từ; không audio, không
đường dẫn tuyệt đối (T-04-05).

`render_report` là hàm thuần (chuỗi ra); `git_sha` là chỗ duy nhất gọi git. Mọi con số trong report
phải do một lần chạy analyze tạo ra ở đúng git sha và versions ghi ở đầu file (minh bạch eval).
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from evalkit.counting import LAYER_C_CODES, POOLED, RuleTally, wilson

HELDOUT_LOCKED = "khoá (D-16)"
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


def _summary_table(tallies: Mapping[str, RuleTally]) -> list[str]:
    lines = [
        "| Rule | TP | FP | Tuning P [CI95] (n) | Tuning R (k/N) [CI95] | Held-out |",
        "|---|---|---|---|---|---|",
    ]
    for code in (*LAYER_C_CODES, POOLED):
        row = tallies.get(code, RuleTally())
        lines.append(
            f"| {code} | {row.tp} | {row.fp} | {_precision_cell(row)} | "
            f"{_recall_cell(row)} | {HELDOUT_LOCKED} |"
        )
    return lines


def render_report(info: RunInfo, tallies: Mapping[str, RuleTally]) -> str:
    """Nội dung `report.md`: tiêu đề, versions/git/chế độ, bảng tóm tắt rule x P/R/n/CI Wilson."""
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
        *_summary_table(tallies),
        "",
    ]
    return "\n".join(lines)

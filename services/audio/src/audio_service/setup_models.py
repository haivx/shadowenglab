"""`python -m audio_service.setup_models`: tải model đã khoá và kiểm tra runtime (FND-04, D-25).

Tải (hoặc tìm trong cache) ba model: whisper-large-v3-turbo, wav2vec2-lv-60-espeak-cv-ft và
Demucs htdemucs, có thanh tiến độ (tqdm của huggingface_hub). Rồi kiểm tra parselmouth,
ffmpeg và MPS, in bảng trạng thái. Chạy lại là no-op khi đã có cache.

Id model chỉ lấy từ `audio_service.models`; không có cờ hay biến môi trường nào ghi đè.
Không nạp gì với remote-code. Chỉ kiểm tra: không cài system package nào.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from audio_service.models import (
    DEMUCS_HF_REPO,
    DEMUCS_MODEL,
    PPG_ALLOW_PATTERNS,
    PPG_REPO,
    WHISPER_REPO,
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = True


def ensure_hf_snapshot(
    repo_id: str, allow_patterns: Sequence[str] | None, *, download: bool
) -> CheckResult:
    """Đảm bảo snapshot HF có trong cache. `download=False` chỉ tìm trong cache."""
    name = repo_id
    try:
        from huggingface_hub import snapshot_download

        path = snapshot_download(
            repo_id=repo_id,
            allow_patterns=list(allow_patterns) if allow_patterns is not None else None,
            local_files_only=not download,
        )
    except Exception as exc:  # noqa: BLE001 - mọi lỗi mạng/cache đều thành một dòng trạng thái
        return CheckResult(name, False, _short(exc))
    verb = "đã tải/có trong cache" if download else "có trong cache"
    return CheckResult(name, True, f"{verb}: {path}")


def ensure_demucs(*, download: bool) -> CheckResult:
    """Demucs 4.1.0 lấy trọng số từ repo HF `DEMUCS_HF_REPO` (hf.py: hf_hub_download).

    Tải: `get_model("hf://htdemucs")` luôn đi qua HF hub, không rơi về repo AWS cũ như
    `get_model("htdemucs")` khi HF lỗi. Chỉ kiểm tra: tìm snapshot trong cache HF.
    """
    name = f"demucs {DEMUCS_MODEL}"
    if not download:
        res = ensure_hf_snapshot(DEMUCS_HF_REPO, None, download=False)
        return CheckResult(name, res.ok, res.detail)
    try:
        from demucs.pretrained import get_model

        get_model(f"hf://{DEMUCS_MODEL}")
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, _short(exc))
    return CheckResult(name, True, f"đã tải/có trong cache HF ({DEMUCS_HF_REPO})")


def check_parselmouth() -> CheckResult:
    name = "parselmouth"
    try:
        import numpy as np
        import parselmouth

        parselmouth.Sound(np.zeros(1600), 16000).to_pitch()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, _short(exc))
    return CheckResult(name, True, f"praat-parselmouth {parselmouth.__version__} chạy được")


def check_ffmpeg() -> CheckResult:
    name = "ffmpeg"
    exe = shutil.which("ffmpeg")
    if exe is None:
        return CheckResult(name, False, "không tìm thấy trong PATH (brew install ffmpeg espeak-ng)")
    try:
        proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return CheckResult(name, False, _short(exc))
    first = proc.stdout.splitlines()[0] if proc.stdout else exe
    return CheckResult(name, True, first)


def check_mps() -> CheckResult:
    name = "mps"
    try:
        import torch

        available = bool(torch.backends.mps.is_available())
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name, False, _short(exc), required=False)
    if available:
        return CheckResult(name, True, "torch MPS khả dụng", required=False)
    return CheckResult(name, False, "MPS không khả dụng, sẽ chạy CPU (chậm hơn)", required=False)


def format_status_table(results: Sequence[CheckResult]) -> str:
    def status(r: CheckResult) -> str:
        if r.ok:
            return "OK"
        return "FAIL" if r.required else "WARN"

    width = max((len(r.name) for r in results), default=4)
    lines = [f"{'check'.ljust(width)}  status  detail", f"{'-' * width}  ------  ------"]
    lines.extend(f"{r.name.ljust(width)}  {status(r):<6}  {r.detail}" for r in results)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m audio_service.setup_models",
        description="Tải model đã khoá và kiểm tra runtime. Không cài system package.",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="chỉ kiểm tra model đã có trong cache, không tải",
    )
    args = parser.parse_args(argv)
    download = not args.no_download

    results = [
        ensure_hf_snapshot(WHISPER_REPO, None, download=download),
        ensure_hf_snapshot(PPG_REPO, PPG_ALLOW_PATTERNS, download=download),
        ensure_demucs(download=download),
        check_parselmouth(),
        check_ffmpeg(),
        check_mps(),
    ]
    print(format_status_table(results))
    return 0 if all(r.ok for r in results if r.required) else 1


def _short(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".strip()
    return text.splitlines()[0][:200] if text else type(exc).__name__


if __name__ == "__main__":
    raise SystemExit(main())

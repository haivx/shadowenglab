"""Chuẩn hoá bản ghi của trình duyệt thành WAV 16 kHz mono PCM16 (REC-02, D-05).

Phần I/O nằm ở rìa: `normalize_to_wav16k` chạy ffmpeg bằng argv list (không shell). Bản ghi là dữ
liệu không tin cậy, nên container được nhận diện từ magic bytes và truyền cho ffmpeg bằng `-f`
tường minh, chỉ gồm hai họ trình duyệt thật sự sinh ra (webm/opus của Chrome, mp4/AAC của Safari).
Không có `-f` thì ffmpeg tự dò và có thể mở playlist m3u8 trỏ tới `file://` hay URL (T-02-25).
Không loudnorm/AGC: Phase 3 so động lực học thô của bản ghi.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

WEBM_DEMUXER = "matroska,webm"
MP4_DEMUXER = "mov,mp4,m4a,3gp,3g2,mj2"

_EBML_MAGIC = b"\x1aE\xdf\xa3"
FFMPEG_TIMEOUT_S = 30.0


def sniff_demuxer(head: bytes) -> str | None:
    """Tên demuxer ffmpeg cho đầu file, hoặc None nếu không phải webm/mp4."""
    if head[:4] == _EBML_MAGIC:
        return WEBM_DEMUXER
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return MP4_DEMUXER
    return None


def normalize_to_wav16k(src: Path, dst: Path, demuxer: str, *, max_seconds: float = 61.0) -> None:
    """ffmpeg: `src` -> WAV 16 kHz mono PCM16 ở `dst`, cắt ở `max_seconds`.

    Raise `subprocess.CalledProcessError` / `subprocess.TimeoutExpired` khi ffmpeg lỗi; stderr
    không được echo ra ngoài (người gọi tự đổi thành lỗi cố định).
    """
    if demuxer not in (WEBM_DEMUXER, MP4_DEMUXER):
        raise ValueError("demuxer ngoài whitelist")
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
        "-f",
        demuxer,
        "-i",
        str(src),
        "-t",
        f"{max_seconds:g}",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(dst),
    ]
    subprocess.run(
        cmd,
        check=True,
        timeout=FFMPEG_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

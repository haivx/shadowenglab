"""Tải video YouTube bằng yt-dlp (Python API), cache theo videoId (D-07).

Biên bảo mật (T-01-15): yt-dlp chỉ bao giờ nhận `canonical_watch_url(video_id)`, không nhận URL
người dùng nhập; không gọi CLI yt-dlp, không qua shell. Mọi đường dẫn đến từ helper config
(đã kiểm tra id). Đây là chỗ DUY NHẤT pipeline ra mạng (local-first, product.md mục 5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp

from audio_service.config import video_asset_path, video_dir
from audio_service.contract_io import write_json_atomic
from audio_service.lesson.urls import canonical_watch_url

# Ảnh/âm thanh chỉ cần cho luyện nói: giữ 480p để tải nhanh. `bv*+ba` rồi mới đến luồng gộp sẵn.
_FORMAT = "bv*[height<=480]+ba/b[height<=480]/b"


@dataclass(frozen=True)
class VideoInfo:
    video_id: str
    title: str
    duration_sec: float
    thumbnail_url: str | None


def _base_opts() -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        # Pitfall 4: yt-dlp cần JS runtime để giải mã YouTube; deno nằm trong venv (extra `deno`).
        "js_runtimes": {"deno": {}},
    }


def _info_path(video_id: str) -> Path:
    return video_dir(video_id) / "info.json"


def fetch_info(video_id: str) -> VideoInfo:
    """Metadata video; cache hit khi `info.json` đã có, nếu không hỏi yt-dlp (download=False)."""
    path = _info_path(video_id)
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return VideoInfo(
            video_id=video_id,
            title=str(cached["title"]),
            duration_sec=float(cached["durationSec"]),
            thumbnail_url=cached.get("thumbnailUrl"),
        )

    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        raw = ydl.extract_info(canonical_watch_url(video_id), download=False)
    if not raw or raw.get("duration") is None:
        raise RuntimeError("yt-dlp không trả về thời lượng video")

    info = VideoInfo(
        video_id=video_id,
        title=str(raw.get("title") or video_id),
        duration_sec=float(raw["duration"]),
        thumbnail_url=raw.get("thumbnail") or None,
    )
    payload: dict[str, object] = {
        "videoId": video_id,
        "title": info.title,
        "durationSec": info.duration_sec,
    }
    if info.thumbnail_url is not None:
        payload["thumbnailUrl"] = info.thumbnail_url
    write_json_atomic(path, payload)
    return info


def download_video(video_id: str) -> Path:
    """Tải video về `videos/{id}/video.mp4`; cache hit thì không tải lại (D-07)."""
    target = video_asset_path(video_id, "video.mp4")
    if target.exists():
        return target

    opts = _base_opts() | {
        "format": _FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": str(video_dir(video_id) / "video.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([canonical_watch_url(video_id)])

    if not target.exists():
        raise RuntimeError("yt-dlp chạy xong nhưng không có video.mp4")
    return target

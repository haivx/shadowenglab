"""Tải video YouTube bằng yt-dlp (Python API), cache theo videoId (D-07).

Biên bảo mật (T-01-15): yt-dlp chỉ bao giờ nhận `canonical_watch_url(video_id)`, không nhận URL
người dùng nhập; không gọi CLI yt-dlp, không qua shell. Mọi đường dẫn đến từ helper config
(đã kiểm tra id). Đây là chỗ DUY NHẤT pipeline ra mạng (local-first, product.md mục 5).
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp

from audio_service.config import video_asset_path, video_dir
from audio_service.contract_io import write_json_atomic
from audio_service.lesson.urls import canonical_watch_url

# D-19: trình duyệt phải phát được. Ưu tiên H.264 (avc1) + AAC (mp4a) <= 480p (chọn 135+140);
# selector cũ giữ làm đường lùi để không bao giờ tải hỏng, `ensure_h264` chuyển mã nếu cần.
_FORMAT = (
    "bv*[height<=480][vcodec^=avc1]+ba[acodec^=mp4a]"
    "/b[height<=480][vcodec^=avc1]"
    "/bv*[height<=480]+ba/b[height<=480]/b"
)

PROBE_TIMEOUT_S = 30
TRANSCODE_TIMEOUT_S = 600

LIVE_STATUSES = frozenset({"is_live", "is_upcoming"})


@dataclass(frozen=True)
class VideoInfo:
    video_id: str
    title: str
    duration_sec: float
    thumbnail_url: str | None
    channel: str | None = None
    live_status: str | None = (
        None  # yt-dlp: not_live | is_live | is_upcoming | was_live | post_live
    )
    availability: str | None = None  # yt-dlp: public | unlisted | private | needs_auth | ...


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
            channel=cached.get("channel"),
            live_status=cached.get("liveStatus"),
            availability=cached.get("availability"),
        )

    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        raw = ydl.extract_info(canonical_watch_url(video_id), download=False)
    if not raw:
        raise RuntimeError("yt-dlp không trả về thông tin video")

    live_status = raw.get("live_status") or None
    is_live = live_status in LIVE_STATUSES
    if raw.get("duration") is None and not is_live:
        raise RuntimeError("yt-dlp không trả về thời lượng video")

    info = VideoInfo(
        video_id=video_id,
        title=str(raw.get("title") or video_id),
        # Livestream / sắp phát chưa có thời lượng: để 0, router xem trước báo `live_video`.
        duration_sec=float(raw["duration"]) if raw.get("duration") is not None else 0.0,
        thumbnail_url=raw.get("thumbnail") or None,
        channel=raw.get("channel") or raw.get("uploader") or None,
        live_status=live_status,
        availability=raw.get("availability") or None,
    )
    if is_live:
        return info  # trạng thái live đổi theo thời gian: không cache

    payload: dict[str, object] = {
        "videoId": video_id,
        "title": info.title,
        "durationSec": info.duration_sec,
    }
    if info.thumbnail_url is not None:
        payload["thumbnailUrl"] = info.thumbnail_url
    if info.channel is not None:
        payload["channel"] = info.channel
    if info.live_status is not None:
        payload["liveStatus"] = info.live_status
    if info.availability is not None:
        payload["availability"] = info.availability
    write_json_atomic(path, payload)
    return info


_VIDEO_LOCKS: dict[str, threading.RLock] = {}
_VIDEO_LOCKS_GUARD = threading.Lock()


def _video_lock(video_id: str) -> threading.RLock:
    """Một khoá cho mỗi video: hai job cùng video (hoặc tải lại) không bao giờ ghi file đồng thời.

    Reentrant vì `reload_video` giữ khoá rồi gọi `download_video`, vốn cũng lấy khoá này.
    Video khác nhau có khoá khác nhau nên vẫn tải song song.
    """
    with _VIDEO_LOCKS_GUARD:
        lock = _VIDEO_LOCKS.get(video_id)
        if lock is None:
            lock = _VIDEO_LOCKS[video_id] = threading.RLock()
        return lock


def probe_video_codec(path: Path) -> str:
    """Tên codec của luồng video đầu tiên (`h264`, `av1`, `vp9`, ...). argv list, không shell."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name",
        "-of",
        "csv=p=0",
        str(path),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True, timeout=PROBE_TIMEOUT_S
    )
    codec = result.stdout.strip().splitlines()[0].strip() if result.stdout.strip() else ""
    if not codec:
        raise RuntimeError("ffprobe không đọc được codec video")
    return codec


def ensure_h264(path: Path) -> None:
    """Chuyển video không phải H.264 sang H.264/AAC (Pitfall 3: AV1/VP9 không phát được ở mọi nơi).

    Ghi ra file tạm cạnh `path` rồi `os.replace`, nên `path` hoặc là bản cũ hoặc là bản mới hoàn
    chỉnh, không bao giờ ghi dở.
    """
    if probe_video_codec(path) == "h264":
        return
    tmp = path.with_name(f"{path.stem}.h264.tmp.mp4")
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "26",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=TRANSCODE_TIMEOUT_S)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _staged_download(folder: Path) -> Path | None:
    """File yt-dlp vừa tải vào `video.dl.*` (mp4 sau khi gộp, nếu không thì file đầu tiên)."""
    preferred = folder / "video.dl.mp4"
    if preferred.is_file():
        return preferred
    leftovers = [p for p in sorted(folder.glob("video.dl.*")) if p.is_file()]
    return leftovers[0] if leftovers else None


def download_video(video_id: str) -> Path:
    """Tải video về `videos/{id}/video.mp4`; cache hit thì không tải lại (D-07).

    Tải vào `video.dl.*`, chuyển mã H.264 nếu cần (D-19), rồi mới `os.replace` thành `video.mp4`:
    file nửa chừng không bao giờ hiện ra dưới tên `video.mp4`. Khoá theo video bao cả bước kiểm
    tra cache lẫn bước tải (PLY-01 concurrency).
    """
    target = video_asset_path(video_id, "video.mp4")
    with _video_lock(video_id):
        if target.exists():
            return target

        folder = video_dir(video_id)
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.glob("video.dl.*"):  # rác của lần tải bị ngắt giữa chừng
            stale.unlink(missing_ok=True)

        opts = _base_opts() | {
            "format": _FORMAT,
            "merge_output_format": "mp4",
            "outtmpl": str(folder / "video.dl.%(ext)s"),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([canonical_watch_url(video_id)])
            staged = _staged_download(folder)
            if staged is None:
                raise RuntimeError("yt-dlp chạy xong nhưng không có file video")
            ensure_h264(staged)
            os.replace(staged, target)
        finally:
            for leftover in folder.glob("video.dl.*"):
                leftover.unlink(missing_ok=True)
        return target


def reload_video(video_id: str, download_fn: Callable[[str], Path]) -> None:
    """Xoá `video.mp4` rồi tải lại (nút "Tải lại video", D-17). Tải lỗi thì trả lại file cũ.

    `download_fn` thường là `download_video`; giữ nguyên khoá video suốt quá trình để không job
    nào ghi chen vào. `audio.wav` và stems không bị đụng tới (không phụ thuộc codec video).
    """
    target = video_asset_path(video_id, "video.mp4")
    backup = video_dir(video_id) / "video.mp4.old"
    with _video_lock(video_id):
        moved = False
        if target.exists():
            os.replace(target, backup)
            moved = True
        try:
            download_fn(video_id)
        except BaseException:
            if moved and not target.exists():
                os.replace(backup, target)
            raise
        backup.unlink(missing_ok=True)

"""download.py: metadata (channel / live_status / availability), H.264 + khoá theo video.

Không mạng, không ffmpeg/ffprobe thật: `yt_dlp.YoutubeDL` và `subprocess.run` là bản giả.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from audio_service.config import get_settings, video_dir
from audio_service.lesson import download

VIDEO_ID = "dUDi-F6eAvk"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


class FakeYoutubeDL:
    """Thay yt_dlp.YoutubeDL cho extract_info (download=False)."""

    raw: dict[str, Any] | None = None

    def __init__(self, opts: dict[str, Any]) -> None:
        self.opts = opts

    def __enter__(self) -> FakeYoutubeDL:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def extract_info(self, _url: str, download: bool = True) -> dict[str, Any] | None:
        assert download is False
        return type(self).raw


def install_fake_ydl(monkeypatch: pytest.MonkeyPatch, raw: dict[str, Any] | None) -> None:
    FakeYoutubeDL.raw = raw
    monkeypatch.setattr(download.yt_dlp, "YoutubeDL", FakeYoutubeDL)


# ------------------------------------------------------------------ fetch_info


def test_fetch_info_reads_old_cache_without_new_keys(data_dir: Path) -> None:
    path = video_dir(VIDEO_ID) / "info.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"videoId": VIDEO_ID, "title": "Old", "durationSec": 61.5}), encoding="utf-8"
    )
    info = download.fetch_info(VIDEO_ID)
    assert (info.title, info.duration_sec) == ("Old", 61.5)
    assert info.thumbnail_url is None
    assert info.channel is None
    assert info.live_status is None
    assert info.availability is None


def test_fetch_info_cache_round_trips_the_new_keys(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(
        monkeypatch,
        {
            "title": "T",
            "duration": 30,
            "channel": "HBO Max",
            "live_status": "not_live",
            "availability": "public",
            "thumbnail": "https://img/x.jpg",
        },
    )
    first = download.fetch_info(VIDEO_ID)
    assert (first.channel, first.live_status, first.availability) == (
        "HBO Max",
        "not_live",
        "public",
    )
    payload = json.loads((video_dir(VIDEO_ID) / "info.json").read_text(encoding="utf-8"))
    assert payload["channel"] == "HBO Max"
    assert payload["liveStatus"] == "not_live"
    assert payload["availability"] == "public"

    install_fake_ydl(monkeypatch, None)  # lần hai phải đọc cache, không hỏi yt-dlp
    assert download.fetch_info(VIDEO_ID) == first


def test_fetch_info_omits_absent_keys_from_the_cache(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(monkeypatch, {"title": "T", "duration": 30})
    info = download.fetch_info(VIDEO_ID)
    assert info.channel is None and info.live_status is None and info.availability is None
    payload = json.loads((video_dir(VIDEO_ID) / "info.json").read_text(encoding="utf-8"))
    for key in ("channel", "liveStatus", "availability", "thumbnailUrl"):
        assert key not in payload


@pytest.mark.parametrize("status", ["is_live", "is_upcoming"])
def test_fetch_info_reports_live_video_without_duration_and_does_not_cache_it(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    install_fake_ydl(monkeypatch, {"title": "Live now", "duration": None, "live_status": status})
    info = download.fetch_info(VIDEO_ID)
    assert info.live_status == status
    assert not (video_dir(VIDEO_ID) / "info.json").exists()  # trạng thái live đổi theo thời gian


def test_fetch_info_still_rejects_a_non_live_video_without_duration(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_ydl(monkeypatch, {"title": "T", "duration": None, "live_status": "not_live"})
    with pytest.raises(RuntimeError):
        download.fetch_info(VIDEO_ID)

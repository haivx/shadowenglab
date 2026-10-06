"""Cổng URL YouTube (RED stub: chưa hiện thực)."""

from __future__ import annotations

import re

ALLOWED_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
MAX_URL_LEN = 2048


class InvalidYoutubeUrl(ValueError):
    pass


def parse_youtube_url(url: str) -> str:
    return ""


def canonical_watch_url(video_id: str) -> str:
    return ""

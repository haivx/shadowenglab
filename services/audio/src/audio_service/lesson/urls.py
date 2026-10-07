"""Cổng URL YouTube: biên tin cậy giữa chuỗi người dùng nhập và yt-dlp / hệ thống file.

Chỉ chấp nhận http(s) tới host YouTube trong allow-list, mang đúng một video id 11 ký tự.
yt-dlp chỉ bao giờ nhận `canonical_watch_url(id)`, không nhận URL gốc. Hàm thuần, không gọi mạng.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

ALLOWED_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"})
VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
MAX_URL_LEN = 2048

_PATH_PREFIXES = ("/shorts/", "/embed/", "/live/")
_CHANNEL_PREFIXES = ("/@", "/channel/", "/c/", "/user/")


class InvalidYoutubeUrl(ValueError):
    """URL không phải link video YouTube hợp lệ."""


def _check_id(video_id: str) -> str:
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise InvalidYoutubeUrl("video id YouTube phải gồm đúng 11 ký tự [A-Za-z0-9_-]")
    return video_id


def parse_youtube_url(url: str) -> str:
    """Trả về video id từ URL YouTube hợp lệ, hoặc raise InvalidYoutubeUrl."""
    if len(url) > MAX_URL_LEN:
        raise InvalidYoutubeUrl("URL quá dài")
    url = url.strip()
    if not url:
        raise InvalidYoutubeUrl("URL rỗng")
    # urlsplit âm thầm bỏ tab/xuống dòng, nên phải loại ký tự điều khiển và khoảng trắng trước.
    if any(ch.isspace() or not ch.isprintable() for ch in url) or "\\" in url:
        raise InvalidYoutubeUrl("URL chứa khoảng trắng hoặc ký tự điều khiển")

    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise InvalidYoutubeUrl("URL không đọc được") from exc

    if parts.scheme not in ("http", "https"):
        raise InvalidYoutubeUrl("chỉ chấp nhận http hoặc https")
    if "@" in parts.netloc:
        raise InvalidYoutubeUrl("URL không được chứa thông tin đăng nhập")
    if port is not None:
        raise InvalidYoutubeUrl("URL không được chỉ định cổng")
    host = parts.hostname
    if host not in ALLOWED_HOSTS:
        raise InvalidYoutubeUrl("host không thuộc YouTube")

    if host == "youtu.be":
        return _check_id(parts.path.split("/")[1] if parts.path.startswith("/") else "")

    if parts.path == "/watch":
        values = parse_qs(parts.query, keep_blank_values=True).get("v", [])
        if len(values) != 1:
            raise InvalidYoutubeUrl("URL phải có đúng một tham số v")
        return _check_id(values[0])

    for prefix in _PATH_PREFIXES:
        if parts.path.startswith(prefix):
            return _check_id(parts.path.removeprefix(prefix).removesuffix("/"))

    raise InvalidYoutubeUrl("đường dẫn không phải một video YouTube")


def canonical_watch_url(video_id: str) -> str:
    """URL chuẩn duy nhất được đưa cho yt-dlp."""
    return f"https://www.youtube.com/watch?v={_check_id(video_id)}"


def is_channel_url(url: str) -> bool:
    """True khi `url` là link kênh YouTube (`/@handle`, `/channel/`, `/c/`, `/user/`).

    Cùng vệ sinh với `parse_youtube_url` (http(s), host allow-list, không user/cổng/khoảng trắng)
    để một link kênh luôn được báo `channel_url` thay vì `invalid_url`. Hàm thuần, không mạng.
    """
    if len(url) > MAX_URL_LEN:
        return False
    url = url.strip()
    if not url or any(ch.isspace() or not ch.isprintable() for ch in url) or "\\" in url:
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or "@" in parts.netloc or port is not None:
        return False
    # youtu.be chỉ có link video ngắn; link kênh chỉ tồn tại trên các host youtube.com.
    if parts.hostname not in ALLOWED_HOSTS or parts.hostname == "youtu.be":
        return False
    return parts.path.startswith(_CHANNEL_PREFIXES)

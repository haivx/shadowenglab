"""Test cổng URL YouTube: allow-list host/scheme, đúng một video id 11 ký tự."""

from __future__ import annotations

import pytest

from audio_service.lesson.urls import (
    ALLOWED_HOSTS,
    MAX_URL_LEN,
    VIDEO_ID_RE,
    InvalidYoutubeUrl,
    canonical_watch_url,
    is_channel_url,
    parse_youtube_url,
)

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"https://www.youtube.com/watch?v={VID}", VID),
        (f"https://youtube.com/watch?v={VID}&t=42", VID),
        (f"https://m.youtube.com/watch?v={VID}", VID),
        (f"https://youtu.be/{VID}?si=x", VID),
        (f"https://www.youtube.com/shorts/{VID}", VID),
        (f"https://www.youtube.com/embed/{VID}", VID),
        (f"https://www.youtube.com/live/{VID}", VID),
        ("http://youtu.be/-abcdefghij", "-abcdefghij"),
        (f"  https://www.youtube.com/watch?v={VID}\n", VID),
        (f"HTTPS://WWW.YOUTUBE.COM/watch?v={VID}", VID),
        (f"https://www.youtube.com/watch?list=PL1&v={VID}", VID),
        ("https://www.youtube.com/watch?v=dUDi-F6eAvk", "dUDi-F6eAvk"),
    ],
)
def test_accepts_youtube_urls_and_returns_id(url: str, expected: str) -> None:
    assert parse_youtube_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        f"https://evil.com/watch?v={VID}",
        f"https://youtube.com.evil.com/watch?v={VID}",
        f"https://notyoutube.com/watch?v={VID}",
        f"https://evil.com/youtube.com/watch?v={VID}",
        f"https://user@youtube.com/watch?v={VID}",
        f"https://user:pw@youtube.com/watch?v={VID}",
        "https://youtube.com@evil.com/watch?v=x",
        f"https://youtube.com@evil.com/watch?v={VID}",
        f"https://youtube.com\\@evil.com/watch?v={VID}",
        "javascript:alert(1)",
        "file:///etc/passwd",
        f"ftp://youtube.com/watch?v={VID}",
        f"//www.youtube.com/watch?v={VID}",
        f"www.youtube.com/watch?v={VID}",
        "https://www.youtube.com/watch?v=short",
        f"https://www.youtube.com/watch?v={VID}X",
        "https://www.youtube.com/watch?v=",
        "https://www.youtube.com/watch",
        f"https://www.youtube.com/watch?v={VID}&v=AAAAAAAAAAA",
        "https://www.youtube.com/playlist?list=PL1",
        f"https://www.youtube.com/user/{VID}",
        f"https://www.youtube.com/?v={VID}",
        f"https://www.youtube.com:8080/watch?v={VID}",
        f"https://www.youtube.com/watch?v={VID[:5]}\n{VID[5:]}",
        f"https://www.youtube.com/watch?v={VID[:5]} {VID[5:]}",
        f"https://www.you\ttube.com/watch?v={VID}",
        f"https://www.youtube.com/watch?v=../../{VID}",
        f"https://youtu.be/{VID[:10]}$",
        "https://youtu.be/",
        "https://youtu.be",
        "--exec=x",
        "-o /tmp/x",
        "",
        "   ",
        "https://www.youtube.com/watch?v=" + "A" * 3000,
        "https://www.youtube.com/watch?v=" + VID + "&pad=" + "a" * 3000,
    ],
)
def test_rejects_other_urls(url: str) -> None:
    with pytest.raises(InvalidYoutubeUrl):
        parse_youtube_url(url)


def test_url_at_length_cap_is_checked_before_parsing() -> None:
    url = f"https://www.youtube.com/watch?v={VID}&x=" + "a" * (MAX_URL_LEN - 50)
    assert len(url) <= MAX_URL_LEN
    assert parse_youtube_url(url) == VID
    with pytest.raises(InvalidYoutubeUrl):
        parse_youtube_url(url + "a" * 100)


def test_invalid_youtube_url_is_a_value_error() -> None:
    assert issubclass(InvalidYoutubeUrl, ValueError)


def test_canonical_watch_url() -> None:
    assert canonical_watch_url(VID) == f"https://www.youtube.com/watch?v={VID}"
    assert canonical_watch_url("-abcdefghij") == "https://www.youtube.com/watch?v=-abcdefghij"


@pytest.mark.parametrize(
    "bad", ["", "short", VID + "x", "--exec=x;ls", "../../etc/pw", "a b c d e f"]
)
def test_canonical_watch_url_rejects_bad_id(bad: str) -> None:
    with pytest.raises(InvalidYoutubeUrl):
        canonical_watch_url(bad)


def test_every_accepted_url_round_trips_to_canonical() -> None:
    url = canonical_watch_url(parse_youtube_url(f"https://youtu.be/{VID}?si=x&t=3"))
    assert url == f"https://www.youtube.com/watch?v={VID}"


def test_allow_list_and_id_pattern() -> None:
    assert ALLOWED_HOSTS == frozenset(
        {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
    )
    assert VIDEO_ID_RE.fullmatch(VID)
    assert not VIDEO_ID_RE.fullmatch(VID + "\n")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@HBOMax",
        "https://youtube.com/@HBOMax/videos",
        "https://www.youtube.com/channel/UCxyz123",
        "https://m.youtube.com/c/foo",
        "https://www.youtube.com/user/foo",
        "  https://www.youtube.com/@HBOMax  ",
        "HTTPS://WWW.YOUTUBE.COM/@HBOMax",
    ],
)
def test_is_channel_url_true_for_channel_links(url: str) -> None:
    assert is_channel_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}",
        f"https://www.youtube.com/shorts/{VID}",
        "https://www.youtube.com/playlist?list=PL1",
        "https://www.youtube.com/",
        "https://example.com/@foo",
        "https://youtu.be/@foo",
        "https://youtube.com.evil.com/@foo",
        "https://user@www.youtube.com/@foo",
        "https://www.youtube.com:8080/@foo",
        "ftp://www.youtube.com/@foo",
        "javascript:alert(1)",
        "www.youtube.com/@foo",
        "https://www.youtube.com/@fo o",
        "https://www.youtube.com/@foo" + "a" * 3000,
        "",
    ],
)
def test_is_channel_url_false_for_everything_else(url: str) -> None:
    assert is_channel_url(url) is False

"""GET /lessons/{id}/video (Range), GET /videos/preview, POST /lessons/{id}/video/reload.

Không gọi mạng, không chạy ffmpeg thật: `fetch_info` / `download_video` là bản giả tiêm qua
PipelineDeps (như test_lessons_api).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from yt_dlp.utils import DownloadError

from audio_service.config import get_settings, lesson_json_path, video_asset_path
from audio_service.lesson import download
from audio_service.lesson.pipeline import PipelineDeps
from audio_service.main import create_app

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"
VIDEO_BYTES = bytes(range(256)) * 16  # 4096 byte


def make_lesson(
    *, lesson_id: str = LESSON_ID, status: str = "ready", video_id: str = VIDEO_ID
) -> dict[str, Any]:
    return {
        "id": lesson_id,
        "videoId": video_id,
        "title": "Demo",
        "durationSec": 12.5,
        "range": {"start": 0.0, "end": 12.5},
        "padMs": 150,
        "status": status,
        "segments": [],
        "createdAt": "2026-10-06T08:00:00.000Z",
    }


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def store_lesson(lesson: dict[str, Any]) -> None:
    path = lesson_json_path(lesson["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson), encoding="utf-8")


def write_video(video_id: str = VIDEO_ID, data: bytes = VIDEO_BYTES) -> Path:
    path = video_asset_path(video_id, "video.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------- GET /lessons/{id}/video


def test_video_full_response_advertises_ranges(client: TestClient) -> None:
    store_lesson(make_lesson())
    write_video()
    res = client.get(f"/lessons/{LESSON_ID}/video")
    assert res.status_code == 200
    assert res.headers["accept-ranges"] == "bytes"
    assert res.headers["content-type"] == "video/mp4"
    assert res.content == VIDEO_BYTES


def test_video_range_request_returns_206_with_content_range(client: TestClient) -> None:
    store_lesson(make_lesson())
    write_video()
    res = client.get(f"/lessons/{LESSON_ID}/video", headers={"Range": "bytes=0-99"})
    assert res.status_code == 206
    assert res.headers["content-range"] == "bytes 0-99/4096"
    assert res.headers["accept-ranges"] == "bytes"
    assert len(res.content) == 100
    assert res.content == VIDEO_BYTES[:100]


def test_video_open_ended_range_reads_the_tail(client: TestClient) -> None:
    store_lesson(make_lesson())
    write_video()
    res = client.get(f"/lessons/{LESSON_ID}/video", headers={"Range": "bytes=4000-"})
    assert res.status_code == 206
    assert res.headers["content-range"] == "bytes 4000-4095/4096"
    assert res.content == VIDEO_BYTES[4000:]


def test_video_unsatisfiable_range_returns_416(client: TestClient) -> None:
    store_lesson(make_lesson())
    write_video()
    res = client.get(f"/lessons/{LESSON_ID}/video", headers={"Range": "bytes=9000-"})
    assert res.status_code == 416


def test_video_concurrent_range_reads_are_independent(client: TestClient) -> None:
    store_lesson(make_lesson())
    write_video()
    first = client.get(f"/lessons/{LESSON_ID}/video", headers={"Range": "bytes=0-9"})
    second = client.get(f"/lessons/{LESSON_ID}/video", headers={"Range": "bytes=100-109"})
    assert first.content == VIDEO_BYTES[0:10]
    assert second.content == VIDEO_BYTES[100:110]


def test_video_not_ready_lesson_is_404_api_error(client: TestClient) -> None:
    store_lesson(make_lesson(status="queued"))
    write_video()
    res = client.get(f"/lessons/{LESSON_ID}/video")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
    assert res.json()["message"] == "Bài chưa sẵn sàng."


def test_video_missing_file_is_404_api_error(client: TestClient) -> None:
    store_lesson(make_lesson())
    res = client.get(f"/lessons/{LESSON_ID}/video")
    assert res.status_code == 404
    assert res.json()["code"] == "not_found"
    assert res.json()["message"] == "Không tìm thấy file video của bài này."


def test_video_unknown_lesson_is_404(client: TestClient) -> None:
    res = client.get(f"/lessons/{LESSON_ID}/video")
    assert res.status_code == 404
    assert res.json() == {"code": "not_found", "message": "Không tìm thấy bài."}


@pytest.mark.parametrize("bad_id", ["abc", "01hzx3y7q8k2m4n6p8r0s2t4v6", "..%2Fetc"])
def test_video_malformed_lesson_id_is_404(client: TestClient, bad_id: str) -> None:
    res = client.get(f"/lessons/{bad_id}/video")
    assert res.status_code == 404


def test_video_response_never_leaks_the_data_dir(client: TestClient, data_dir: Path) -> None:
    store_lesson(make_lesson(status="queued"))
    for url in (f"/lessons/{LESSON_ID}/video", "/lessons/abc/video"):
        assert str(data_dir) not in client.get(url).text
    store_lesson(make_lesson())
    assert str(data_dir) not in client.get(f"/lessons/{LESSON_ID}/video").text


# ---------------------------------------------------------------- GET /videos/preview

CHANNEL_MSG = "Đây là link kênh. Hãy dán link một video (có “watch?v=” hoặc “youtu.be/”)."
INVALID_URL_MSG = (
    "Link này không phải link video YouTube. Hãy dán link có “watch?v=” hoặc “youtu.be/”."
)
UNAVAILABLE_MSG = (
    "Không lấy được video này (giới hạn khu vực, video riêng tư hoặc livestream). Thử video khác."
)
WATCH_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


class MediaFakes:
    """`fetch_info` / `download_video` giả; các stage còn lại không bao giờ chạy ở đây."""

    def __init__(
        self,
        info: download.VideoInfo | None = None,
        error: Exception | None = None,
    ) -> None:
        self.info = info or download.VideoInfo(
            VIDEO_ID, "Fake title", 12.5, "https://img/t.jpg", channel="Fake channel"
        )
        self.error = error
        self.calls: list[str] = []
        self.download_calls: list[str] = []
        self.download_error: Exception | None = None
        self.file_existed_at_download: list[bool] = []

    def fetch_info(self, video_id: str) -> download.VideoInfo:
        self.calls.append(video_id)
        if self.error is not None:
            raise self.error
        return self.info

    def download_video(self, video_id: str) -> Path:
        self.download_calls.append(video_id)
        path = video_asset_path(video_id, "video.mp4")
        self.file_existed_at_download.append(path.exists())
        if self.download_error is not None:
            raise self.download_error
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"new video bytes")
        return path

    def deps(self) -> PipelineDeps:
        def unused(*_a: object, **_k: object) -> Any:
            raise AssertionError("stage không được gọi trong test này")

        return PipelineDeps(
            fetch_info=self.fetch_info,
            download_video=self.download_video,
            extract_audio=unused,
            separate=unused,
            transcribe=unused,
            load_ppg=unused,
            compute_ppg=unused,
            extract_f0=unused,
            frame_energy=unused,
            free_memory=lambda: None,
        )


def make_client(fakes: MediaFakes) -> TestClient:
    return TestClient(create_app(deps=fakes.deps()), base_url="http://127.0.0.1")


def preview(client: TestClient, url: str) -> Any:
    return client.get("/videos/preview", params={"url": url})


def test_preview_returns_video_preview(data_dir: Path) -> None:
    fakes = MediaFakes()
    with make_client(fakes) as client:
        res = preview(client, WATCH_URL)
    assert res.status_code == 200
    assert res.json() == {
        "videoId": VIDEO_ID,
        "title": "Fake title",
        "durationSec": 12.5,
        "channel": "Fake channel",
        "thumbnailUrl": "https://img/t.jpg",
    }
    assert fakes.calls == [VIDEO_ID]  # yt-dlp chỉ nhận video id đã kiểm tra


def test_preview_omits_absent_optionals(data_dir: Path) -> None:
    fakes = MediaFakes(info=download.VideoInfo(VIDEO_ID, "T", 30.0, None))
    with make_client(fakes) as client:
        body = preview(client, WATCH_URL).json()
    assert body == {"videoId": VIDEO_ID, "title": "T", "durationSec": 30.0}


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@HBOMax",
        "https://www.youtube.com/channel/UCxyz123",
        "https://www.youtube.com/c/foo",
        "https://www.youtube.com/user/foo",
    ],
)
def test_preview_channel_link_is_400_channel_url(data_dir: Path, url: str) -> None:
    fakes = MediaFakes()
    with make_client(fakes) as client:
        res = preview(client, url)
    assert res.status_code == 400
    assert res.json() == {"code": "channel_url", "message": CHANNEL_MSG}
    assert fakes.calls == []


@pytest.mark.parametrize(
    "url", ["https://example.com", "not a url", "https://www.youtube.com/playlist?list=PL1", " "]
)
def test_preview_invalid_link_is_400_invalid_url(data_dir: Path, url: str) -> None:
    fakes = MediaFakes()
    with make_client(fakes) as client:
        res = preview(client, url)
    assert res.status_code == 400
    assert res.json() == {"code": "invalid_url", "message": INVALID_URL_MSG}
    assert fakes.calls == []


def test_preview_download_error_is_404_without_ytdlp_text(data_dir: Path) -> None:
    secret = "ERROR: [youtube] dUDi-F6eAvk: Private video. Sign in /Users/liam/secret"
    fakes = MediaFakes(error=DownloadError(secret))
    with make_client(fakes) as client:
        res = preview(client, WATCH_URL)
    assert res.status_code == 404
    assert res.json() == {"code": "video_unavailable", "message": UNAVAILABLE_MSG}
    assert "Private" not in res.text and "/Users" not in res.text


def test_preview_unexpected_error_is_502_without_leak(data_dir: Path) -> None:
    fakes = MediaFakes(error=RuntimeError("boom /Users/liam/x"))
    with make_client(fakes) as client:
        res = preview(client, WATCH_URL)
    assert res.status_code == 502
    assert res.json()["code"] == "upstream_error"
    assert "boom" not in res.text and "/Users" not in res.text


@pytest.mark.parametrize("status", ["is_live", "is_upcoming"])
def test_preview_live_or_upcoming_is_422_live_video(data_dir: Path, status: str) -> None:
    info = download.VideoInfo(VIDEO_ID, "Live", 0.0, None, live_status=status)
    with make_client(MediaFakes(info=info)) as client:
        res = preview(client, WATCH_URL)
    assert res.status_code == 422
    assert res.json() == {"code": "live_video", "message": UNAVAILABLE_MSG}


@pytest.mark.parametrize(
    "availability", ["private", "needs_auth", "subscriber_only", "premium_only"]
)
def test_preview_restricted_availability_is_404(data_dir: Path, availability: str) -> None:
    info = download.VideoInfo(VIDEO_ID, "T", 30.0, None, availability=availability)
    with make_client(MediaFakes(info=info)) as client:
        res = preview(client, WATCH_URL)
    assert res.status_code == 404
    assert res.json() == {"code": "video_unavailable", "message": UNAVAILABLE_MSG}


@pytest.mark.parametrize("availability", ["public", "unlisted", None])
def test_preview_public_availability_is_ok(data_dir: Path, availability: str | None) -> None:
    info = download.VideoInfo(VIDEO_ID, "T", 30.0, None, availability=availability)
    with make_client(MediaFakes(info=info)) as client:
        assert preview(client, WATCH_URL).status_code == 200


def test_preview_url_over_2048_chars_is_rejected(data_dir: Path) -> None:
    with make_client(MediaFakes()) as client:
        res = preview(client, WATCH_URL + "&x=" + "a" * 2100)
    assert res.status_code == 422
    assert res.json()["code"] == "invalid_request"


def test_preview_flags_existing_lesson_for_default_range(data_dir: Path) -> None:
    store_lesson(make_lesson())  # ready, 0 - 12.5 = khoảng mặc định của video 12.5 s
    with make_client(MediaFakes()) as client:
        body = preview(client, WATCH_URL).json()
    assert body["existingLessonId"] == LESSON_ID


def test_preview_ignores_failed_lesson(data_dir: Path) -> None:
    store_lesson(make_lesson(status="failed"))
    with make_client(MediaFakes()) as client:
        assert "existingLessonId" not in preview(client, WATCH_URL).json()


def test_preview_ignores_lesson_with_other_range_or_video(data_dir: Path) -> None:
    other_range = make_lesson()
    other_range["range"] = {"start": 2.0, "end": 10.0}
    store_lesson(other_range)
    store_lesson(make_lesson(lesson_id="01HZX3Y7Q8K2M4N6P8R0S2T4V7", video_id="aaaaaaaaaaa"))
    with make_client(MediaFakes()) as client:
        assert "existingLessonId" not in preview(client, WATCH_URL).json()


def test_preview_uses_five_minute_default_for_long_video(data_dir: Path) -> None:
    long_info = download.VideoInfo(VIDEO_ID, "Long", 900.0, None)
    lesson = make_lesson()
    lesson["durationSec"] = 900.0
    lesson["range"] = {"start": 0.0, "end": 300.0}
    store_lesson(lesson)
    with make_client(MediaFakes(info=long_info)) as client:
        assert preview(client, WATCH_URL).json()["existingLessonId"] == LESSON_ID


# ---------------------------------------------------------------- POST /lessons/{id}/video/reload


def reload_video(client: TestClient, lesson_id: str = LESSON_ID) -> Any:
    return client.post(f"/lessons/{lesson_id}/video/reload")


def test_reload_redownloads_after_removing_the_old_file(data_dir: Path) -> None:
    store_lesson(make_lesson())
    path = write_video()
    fakes = MediaFakes()
    with make_client(fakes) as client:
        res = reload_video(client)
    assert res.status_code == 204
    assert res.content == b""
    assert fakes.download_calls == [VIDEO_ID]
    assert fakes.file_existed_at_download == [False]  # file cũ đã được gỡ trước khi tải
    assert path.read_bytes() == b"new video bytes"


def test_reload_keeps_cached_audio_and_stems(data_dir: Path) -> None:
    store_lesson(make_lesson())
    write_video()
    wav = video_asset_path(VIDEO_ID, "audio.wav")
    wav.write_bytes(b"wav")
    with make_client(MediaFakes()) as client:
        assert reload_video(client).status_code == 204
    assert wav.read_bytes() == b"wav"


def test_reload_on_not_ready_lesson_is_409_invalid_state(data_dir: Path) -> None:
    store_lesson(make_lesson(status="queued"))
    fakes = MediaFakes()
    with make_client(fakes) as client:
        res = reload_video(client)
    assert res.status_code == 409
    assert res.json() == {"code": "invalid_state", "message": "Bài chưa sẵn sàng."}
    assert fakes.download_calls == []


def test_reload_unknown_or_malformed_lesson_is_404(data_dir: Path) -> None:
    with make_client(MediaFakes()) as client:
        assert reload_video(client).status_code == 404
        assert reload_video(client, "abc").status_code == 404


def test_reload_download_error_is_502_and_keeps_the_old_file(data_dir: Path) -> None:
    store_lesson(make_lesson())
    path = write_video()
    fakes = MediaFakes()
    fakes.download_error = DownloadError("ERROR: HTTP 403 /Users/liam/secret")
    with make_client(fakes) as client:
        res = reload_video(client)
    assert res.status_code == 502
    assert res.json() == {"code": "video_unavailable", "message": UNAVAILABLE_MSG}
    assert "403" not in res.text and "/Users" not in res.text
    assert path.read_bytes() == VIDEO_BYTES  # tải lỗi thì video cũ còn nguyên


def test_reload_unexpected_error_is_502_upstream_error_without_leak(data_dir: Path) -> None:
    store_lesson(make_lesson())
    write_video()
    fakes = MediaFakes()
    fakes.download_error = RuntimeError("ffmpeg exploded /Users/liam/x")
    with make_client(fakes) as client:
        res = reload_video(client)
    assert res.status_code == 502
    assert res.json()["code"] == "upstream_error"
    assert "ffmpeg" not in res.text and "/Users" not in res.text

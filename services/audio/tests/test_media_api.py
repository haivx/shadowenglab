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

from audio_service.config import get_settings, lesson_json_path, video_asset_path
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

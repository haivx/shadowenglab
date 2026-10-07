"""POST /lessons -> JobRunner -> lesson.json ready, quan sát qua GET /lessons/{id} (D-01, D-06).

Không nạp model, không gọi mạng: stage nặng là bản giả tiêm qua PipelineDeps. Lifespan (runner)
chỉ chạy bên trong `with TestClient(...)`.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from yt_dlp.utils import DownloadError

from audio_service.config import get_settings, lesson_json_path, video_asset_path
from audio_service.contracts_gen import ApiError, Lesson
from audio_service.lesson import store
from audio_service.lesson.audio_io import write_audio
from audio_service.lesson.download import VideoInfo
from audio_service.lesson.pipeline import PipelineDeps
from audio_service.lesson.segment import AsrWord
from audio_service.main import create_app

VIDEO_ID = "dUDi-F6eAvk"
URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
SR = 44100
AUDIO_SECONDS = 12.0
FULL_SEQUENCE = [
    "queued",
    "downloading",
    "queued",
    "separating",
    "transcribing",
    "segmenting",
    "analyzing",
    "ready",
]

# Mỗi câu >= 3 s (MIN_DUR_S, D-21) để split_sentences cho đúng 2 segment.
_WORDS = [
    (" Hello", 0.5, 1.1, 0.9),
    (" there,", 1.2, 1.9, 0.8),
    (" my", 2.0, 2.4, 0.95),
    (" friend.", 2.5, 3.8, 0.7),
    (" How", 4.4, 4.8, 0.9),
    (" are", 4.9, 5.3, 0.85),
    (" you", 5.4, 5.8, 0.99),
    (" today?", 5.9, 7.6, 0.6),
]


class Fakes:
    """Stage giả tối thiểu; `duration` là độ dài video báo cho API, audio thật luôn 12 s."""

    def __init__(
        self, *, duration: float = AUDIO_SECONDS, fetch_error: Exception | None = None
    ) -> None:
        self.duration = duration
        self.fetch_error = fetch_error
        self.download_error: Exception | None = None

    def deps(self) -> PipelineDeps:
        return PipelineDeps(
            fetch_info=self.fetch_info,
            download_video=self.download_video,
            extract_audio=self.extract_audio,
            separate=self.separate,
            transcribe=self.transcribe,
            load_ppg=lambda: object(),
            compute_ppg=lambda clip, _m: np.full((max(len(clip) // 320, 1), 5), 0.2, np.float32),
            extract_f0=lambda clip: np.zeros(max(len(clip) // 160, 1), dtype=np.float32),
            frame_energy=lambda clip: np.zeros(max(len(clip) // 160, 1), dtype=np.float32),
            free_memory=lambda: None,
        )

    def fetch_info(self, video_id: str) -> VideoInfo:
        if self.fetch_error is not None:
            raise self.fetch_error
        return VideoInfo(video_id, "Fake title", self.duration, None)

    def download_video(self, video_id: str) -> Path:
        if self.download_error is not None:
            raise self.download_error
        path = video_asset_path(video_id, "video.mp4")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"not a real video")
        return path

    def extract_audio(self, _video_path: Path, wav_path: Path) -> None:
        t = np.arange(int(SR * AUDIO_SECONDS)) / SR
        tone = (0.3 * np.sin(2 * math.pi * 220.0 * t)).astype(np.float32)
        write_audio(wav_path, np.stack([tone, tone]), SR)

    def separate(self, stereo: np.ndarray, _sr: int) -> tuple[np.ndarray, np.ndarray]:
        return (0.9 * stereo).astype(np.float32), (0.1 * stereo).astype(np.float32)

    def transcribe(self, _audio16k: np.ndarray, *, offset_s: float) -> list[AsrWord]:
        return [AsrWord(t, s + offset_s, e + offset_s, p) for t, s, e, p in _WORDS]


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


@pytest.fixture
def saved_statuses(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Mọi `status` đã ghi xuống đĩa qua store.save_lesson, theo thứ tự."""
    seen: list[str] = []
    real_save = store.save_lesson

    def recording_save(lesson: Lesson) -> None:
        real_save(lesson)
        seen.append(lesson.status)

    monkeypatch.setattr(store, "save_lesson", recording_save)
    return seen


def make_client(fakes: Fakes) -> TestClient:
    return TestClient(create_app(deps=fakes.deps()), base_url="http://127.0.0.1")


def wait_for_status(
    client: TestClient, lesson_id: str, wanted: set[str], timeout_s: float = 5.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while True:
        res = client.get(f"/lessons/{lesson_id}")
        assert res.status_code == 200
        body: dict[str, Any] = res.json()
        if body["status"] in wanted:
            return body
        assert time.monotonic() < deadline, f"bài kẹt ở {body['status']}"
        time.sleep(0.02)


def test_post_lessons_returns_queued_then_runner_advances_to_ready(
    data_dir: Path, saved_statuses: list[str]
) -> None:
    with make_client(Fakes()) as client:
        res = client.post("/lessons", json={"url": URL})

        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "queued"
        assert body["videoId"] == VIDEO_ID
        assert body["range"] == {"start": 0.0, "end": AUDIO_SECONDS}
        assert body["segments"] == []
        assert "error" not in body

        final = wait_for_status(client, body["id"], {"ready", "failed"})

    assert final["status"] == "ready"
    assert len(final["segments"]) == 2
    assert saved_statuses == FULL_SEQUENCE
    Lesson.model_validate(json.loads(lesson_json_path(body["id"]).read_text(encoding="utf-8")))


def test_invalid_url_is_400_api_error_and_creates_nothing(data_dir: Path) -> None:
    with make_client(Fakes()) as client:
        res = client.post("/lessons", json={"url": "https://evil.example/watch?v=dUDi-F6eAvk"})

    assert res.status_code == 400
    error = ApiError.model_validate(res.json())
    assert error.code == "invalid_url"
    assert "lessonId" not in res.json()
    assert not (data_dir / "lessons").exists()


def test_same_url_and_range_again_is_409_duplicate_with_lesson_id(data_dir: Path) -> None:
    with make_client(Fakes()) as client:
        first = client.post("/lessons", json={"url": URL}).json()
        second = client.post("/lessons", json={"url": URL})
        wait_for_status(client, first["id"], {"ready", "failed"})

    assert second.status_code == 409
    error = ApiError.model_validate(second.json())
    assert error.code == "duplicate_lesson"
    assert second.json()["lessonId"] == first["id"]


def test_a_different_range_of_the_same_video_is_not_a_duplicate(data_dir: Path) -> None:
    with make_client(Fakes()) as client:
        first = client.post("/lessons", json={"url": URL, "start": 0, "end": 6})
        second = client.post("/lessons", json={"url": URL, "start": 2, "end": 8})
        for res in (first, second):
            wait_for_status(client, res.json()["id"], {"ready", "failed"})

    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_long_video_without_a_range_defaults_to_the_first_five_minutes(data_dir: Path) -> None:
    with make_client(Fakes(duration=400.0)) as client:
        res = client.post("/lessons", json={"url": URL})
        wait_for_status(client, res.json()["id"], {"ready", "failed"})

    assert res.status_code == 201
    assert res.json()["range"] == {"start": 0.0, "end": 300.0}


def test_video_of_exactly_six_minutes_uses_the_whole_video(data_dir: Path) -> None:
    with make_client(Fakes(duration=360.0)) as client:
        res = client.post("/lessons", json={"url": URL})
        wait_for_status(client, res.json()["id"], {"ready", "failed"})

    assert res.json()["range"] == {"start": 0.0, "end": 360.0}


@pytest.mark.parametrize(
    "payload", [{"start": 5, "end": 5}, {"start": 8, "end": 2}, {"start": 20}], ids=str
)
def test_bad_range_is_422_invalid_range(data_dir: Path, payload: dict[str, float]) -> None:
    with make_client(Fakes()) as client:
        res = client.post("/lessons", json={"url": URL, **payload})

    assert res.status_code == 422
    assert ApiError.model_validate(res.json()).code == "invalid_range"
    assert not (data_dir / "lessons").exists()


def test_fetch_info_download_error_is_404_video_unavailable(data_dir: Path) -> None:
    fakes = Fakes(fetch_error=DownloadError("ERROR: Private video /secret/path"))
    with make_client(fakes) as client:
        res = client.post("/lessons", json={"url": URL})

    assert res.status_code == 404
    assert ApiError.model_validate(res.json()).code == "video_unavailable"
    assert "secret" not in res.text and "ERROR" not in res.text


def test_blocked_download_fails_the_lesson_with_a_fixed_vietnamese_message(
    data_dir: Path,
) -> None:
    fakes = Fakes()
    fakes.download_error = DownloadError("ERROR: HTTP 403 /Users/liam/secret.mp4")
    with make_client(fakes) as client:
        created = client.post("/lessons", json={"url": URL}).json()
        final = wait_for_status(client, created["id"], {"ready", "failed"})

    assert final["status"] == "failed"
    assert final["error"] == {
        "step": "downloading",
        "message": "video bị giới hạn khu vực, riêng tư hoặc tắt tải xuống",
    }


def test_unexpected_error_stores_generic_text_without_exception_or_path(data_dir: Path) -> None:
    fakes = Fakes()
    fakes.download_error = ConnectionError(f"boom {data_dir}/videos/x")
    with make_client(fakes) as client:
        created = client.post("/lessons", json={"url": URL}).json()
        final = wait_for_status(client, created["id"], {"ready", "failed"})

    assert final["status"] == "failed"
    assert final["error"]["message"] == "lỗi không mong đợi (xem log của make dev)"
    raw = lesson_json_path(created["id"]).read_text(encoding="utf-8")
    assert "boom" not in raw and str(data_dir) not in raw

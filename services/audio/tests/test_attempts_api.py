"""Test POST /lessons/{id}/segments/{i}/attempts với ffmpeg thật (REC-02, REC-03, REC-04)."""

from __future__ import annotations

import json
import math
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from audio_service.config import get_settings, lesson_json_path
from audio_service.main import create_app

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
QUEUED_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V7"
SR = 16000


def voice_like(seconds: float = 2.0) -> np.ndarray:
    """Âm 200 Hz có đường bao biên độ, nền rất nhỏ ở hai đầu: giống một câu nói ngắn."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    # Tiếng ở giữa (khoảng 0.5 s .. seconds - 0.5 s), hai đầu chỉ có nền ồn.
    envelope = np.clip(np.minimum(t - 0.5, seconds - 0.5 - t) * 10.0, 0.0, 1.0)
    tone = 0.3 * np.sin(2 * math.pi * 200 * t) * envelope
    noise = np.random.default_rng(0).normal(0, 1e-4, n)
    return (tone + noise).astype(np.float32)


def silence(seconds: float = 2.0) -> np.ndarray:
    return np.zeros(int(SR * seconds), dtype=np.float32)


def encode(audio: np.ndarray, out: Path, *codec_args: str) -> bytes:
    """Mã hoá mảng thành container qua ffmpeg thật; trả bytes của file."""
    wav = out.with_suffix(".src.wav")
    sf.write(wav, audio, SR, subtype="PCM_16")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(wav), *codec_args, str(out)],
        check=True,
    )
    return out.read_bytes()


def webm(audio: np.ndarray, tmp: Path, name: str = "rec.webm") -> bytes:
    return encode(audio, tmp / name, "-c:a", "libopus")


def make_lesson(lesson_id: str, status: str = "ready", segments: int = 1) -> dict[str, Any]:
    return {
        "id": lesson_id,
        "videoId": "dUDi-F6eAvk",
        "title": "Lesson",
        "durationSec": 12.5,
        "range": {"start": 0.0, "end": 12.5},
        "padMs": 150,
        "status": status,
        "segments": [
            {
                "index": i,
                "text": f"Sentence {i}",
                "start": float(i),
                "end": float(i) + 0.9,
                "endExtraMs": 0,
                "words": [
                    {
                        "i": 0,
                        "text": "Sentence",
                        "start": float(i),
                        "end": float(i) + 0.9,
                        "asrProb": 0.95,
                    }
                ],
            }
            for i in range(segments)
        ],
        "createdAt": "2026-10-07T08:00:00.000Z",
    }


def store(lesson: dict[str, Any]) -> None:
    path = lesson_json_path(lesson["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson), encoding="utf-8")


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_DIR", str(root))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    store(make_lesson(LESSON_ID))
    store(make_lesson(QUEUED_ID, status="queued", segments=0))
    return TestClient(create_app(), base_url="http://127.0.0.1")


def post(
    client: TestClient,
    body: bytes,
    *,
    lesson_id: str = LESSON_ID,
    index: int = 0,
    save: bool | None = None,
    filename: str = "rec.webm",
) -> Any:
    data = {} if save is None else {"saveForEval": "true" if save else "false"}
    return client.post(
        f"/lessons/{lesson_id}/segments/{index}/attempts",
        files={"audio": (filename, body, "application/octet-stream")},
        data=data,
    )


def tmp_files(data_dir: Path) -> list[Path]:
    root = data_dir / "tmp"
    return sorted(root.rglob("*")) if root.exists() else []


def test_spoken_then_silent_recording_are_recorded(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    spoken = post(client, webm(voice_like(), tmp_path))

    assert spoken.status_code == 201
    body = spoken.json()
    assert body["lessonId"] == LESSON_ID
    assert body["segmentIndex"] == 0
    assert body["attempt"] == 1
    assert body["voiced"] is True
    assert body["savedForEval"] is False
    assert abs(body["durationMs"] - 2000) <= 60

    quiet = post(client, webm(silence(), tmp_path, "quiet.webm"))

    assert quiet.status_code == 201
    assert quiet.json()["voiced"] is False
    assert quiet.json()["attempt"] == 2  # lượt im lặng vẫn ghi một dòng (02-01 mục C)
    assert tmp_files(data_dir) == []


def test_safari_mp4_and_fragmented_mp4_are_accepted(client: TestClient, tmp_path: Path) -> None:
    plain = encode(voice_like(), tmp_path / "rec.mp4", "-c:a", "aac")
    fragmented = encode(
        voice_like(),
        tmp_path / "frag.mp4",
        "-c:a",
        "aac",
        "-movflags",
        "frag_keyframe+empty_moov",
    )

    for body in (plain, fragmented):
        res = post(client, body, filename="rec.mp4")
        assert res.status_code == 201
        assert res.json()["voiced"] is True


def test_queued_lesson_is_409_invalid_state(client: TestClient, tmp_path: Path) -> None:
    res = post(client, webm(voice_like(), tmp_path), lesson_id=QUEUED_ID)

    assert res.status_code == 409
    assert res.json()["code"] == "invalid_state"


def test_segment_index_out_of_range_is_404_invalid_segment(
    client: TestClient, tmp_path: Path
) -> None:
    res = post(client, webm(voice_like(), tmp_path), index=5)

    assert res.status_code == 404
    assert res.json()["code"] == "invalid_segment"


def test_unknown_lesson_is_404_not_found(client: TestClient, tmp_path: Path) -> None:
    res = post(client, webm(voice_like(), tmp_path), lesson_id="01HZX3Y7Q8K2M4N6P8R0S2T4V9")

    assert res.status_code == 404
    assert res.json()["code"] == "not_found"

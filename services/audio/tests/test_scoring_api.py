"""POST /lessons/{id}/segments/{i}/attempts chấm thật trên stem tổng hợp (03-05, PRO-03, PRO-04).

Bản gốc là `synth_sentence(DEFAULT_WORDS)` ghi thành `vocals.wav` của stem; người học tải đúng câu
đó lên (webm/opus qua ffmpeg thật). Không có audio thật trong repo.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from scipy.signal import resample_poly
from synth import DEFAULT_WORDS, synth_sentence

from audio_service import db
from audio_service.config import (
    get_settings,
    lesson_json_path,
    ref_prosody_path,
    stems_dir,
)
from audio_service.contracts_gen import ScoreResult
from audio_service.main import create_app

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"
SR = 16000
REQUIRED_TIMING_KEYS = {"normalize", "ref_features", "user_features", "align", "metrics", "rules"}


def sentence() -> tuple[np.ndarray, list[tuple[str, float, float]]]:
    return synth_sentence(DEFAULT_WORDS)


def scoring_lesson(
    lesson_id: str = LESSON_ID, *, status: str = "ready", segments: int = 1
) -> dict[str, Any]:
    """Bài `ready` mà câu 0 mang đúng mốc từ của câu tổng hợp (stem bắt đầu ở giây tuyệt đối 0)."""
    _, marks = sentence()
    built: list[dict[str, Any]] = []
    for i in range(segments):
        built.append(
            {
                "index": i,
                "text": f"Sentence {i}",
                "start": marks[0][1],
                "end": marks[-1][2],
                "endExtraMs": 0,
                "words": [
                    {"i": w, "text": text, "start": start, "end": end, "asrProb": 0.95}
                    for w, (text, start, end) in enumerate(marks)
                ],
            }
        )
    return {
        "id": lesson_id,
        "videoId": VIDEO_ID,
        "title": "Lesson",
        "durationSec": 12.5,
        "range": {"start": 0.0, "end": 12.5},
        "padMs": 150,
        "status": status,
        "segments": built if status == "ready" else [],
        "createdAt": "2026-10-07T08:00:00.000Z",
    }


def store_lesson(lesson: dict[str, Any]) -> None:
    path = lesson_json_path(lesson["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson), encoding="utf-8")


def write_stem(audio: np.ndarray, *, sr: int = SR, channels: int = 1) -> Path:
    """Ghi `vocals.wav` đúng chỗ pipeline đọc (`videos/{id}/stems/{start_ms}-{end_ms}`)."""
    folder = stems_dir(VIDEO_ID, 0, 12500)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "vocals.wav"
    data = audio if channels == 1 else np.stack([audio] * channels, axis=1)
    sf.write(path, data, sr, subtype="FLOAT", format="WAV")
    return path


def encode_webm(audio: np.ndarray, tmp: Path, name: str = "rec.webm") -> bytes:
    wav = tmp / f"{name}.src.wav"
    out = tmp / name
    sf.write(wav, audio, SR, subtype="PCM_16")
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(wav),
            "-c:a",
            "libopus",
            str(out),
        ],
        check=True,
    )
    return out.read_bytes()


def upload(client: TestClient, body: bytes, *, lesson_id: str = LESSON_ID, index: int = 0) -> Any:
    return client.post(
        f"/lessons/{lesson_id}/segments/{index}/attempts",
        files={"audio": ("rec.webm", body, "application/octet-stream")},
    )


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
    store_lesson(scoring_lesson())
    write_stem(sentence()[0])
    return TestClient(create_app(), base_url="http://127.0.0.1", raise_server_exceptions=False)


@pytest.fixture
def recording(tmp_path: Path) -> bytes:
    return encode_webm(sentence()[0], tmp_path)


def stored_row(attempt: int) -> dict[str, Any]:
    with db.connection() as conn:
        row = conn.execute(
            "SELECT overall, intonation, rhythm, sound, result_json, voiced FROM attempts "
            "WHERE lesson_id = ? AND segment_index = 0 AND attempt = ?",
            (LESSON_ID, attempt),
        ).fetchone()
    assert row is not None
    return dict(row)


# --- Task 1: tracer ---------------------------------------------------------------------------


def test_self_upload_is_scored_stored_and_numbered(client: TestClient, recording: bytes) -> None:
    res = upload(client, recording)

    assert res.status_code == 201, res.text
    body = res.json()
    assert "scores" in body, body  # D-09: 201 mang ScoreResult, không còn AttemptAck
    result = ScoreResult.model_validate(body)
    assert body["attempt"] == 1
    assert body["lessonId"] == LESSON_ID
    assert body["segmentIndex"] == 0
    assert body["scores"]["sound"] is None
    assert body["scores"]["overall"] >= 0.95  # PRO-03: bản gốc tự so (đã qua opus)
    assert REQUIRED_TIMING_KEYS | {"total", "ref_backfill"} <= set(body["timingMs"])
    row = stored_row(1)
    assert row["overall"] == pytest.approx(result.scores.overall)
    assert row["voiced"] == 1
    assert row["sound"] is None
    assert ScoreResult.model_validate_json(row["result_json"]) == result


def test_first_scoring_backfills_the_sidecar_and_second_is_cached_and_fast(
    client: TestClient, recording: bytes
) -> None:
    assert not ref_prosody_path(LESSON_ID, 0).exists()

    first = upload(client, recording)
    assert first.status_code == 201
    assert ref_prosody_path(LESSON_ID, 0).is_file()

    started = time.perf_counter()
    second = upload(client, recording)
    wall = time.perf_counter() - started

    assert second.status_code == 201
    body = second.json()
    assert body["attempt"] == 2
    assert "ref_backfill" not in body["timingMs"]
    assert REQUIRED_TIMING_KEYS | {"total"} <= set(body["timingMs"])
    assert body["timingMs"]["total"] < 3000
    assert wall < 3.0
    print(
        f"\nPRO-04 cached: wall={wall * 1000:.0f} ms overall={body['scores']['overall']:.4f} "
        f"timingMs={ {k: round(v, 1) for k, v in body['timingMs'].items()} }"
    )
    print(
        f"first (backfill) overall={first.json()['scores']['overall']:.4f} "
        f"timingMs={ {k: round(v, 1) for k, v in first.json()['timingMs'].items()} }"
    )


def test_no_temp_files_remain_after_scoring(
    client: TestClient, recording: bytes, data_dir: Path
) -> None:
    assert upload(client, recording).status_code == 201
    tmp = data_dir / "tmp"
    assert [p for p in tmp.rglob("*")] == []


def test_stereo_44k_stem_is_read_by_slice_and_scores_high(data_dir: Path, tmp_path: Path) -> None:
    store_lesson(scoring_lesson())
    audio, _ = sentence()
    up = resample_poly(audio, 441, 160).astype(np.float32)
    write_stem(up, sr=44100, channels=2)
    client = TestClient(create_app(), base_url="http://127.0.0.1", raise_server_exceptions=False)

    res = upload(client, encode_webm(audio, tmp_path))

    assert res.status_code == 201, res.text
    assert res.json()["scores"]["overall"] >= 0.9

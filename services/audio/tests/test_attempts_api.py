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

from audio_service import db
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


# --- Task 2: whitelist container, giới hạn kích thước / thời lượng ----------------------------

MAX_BYTES = 10 * 1024 * 1024
WEBM_MAGIC = b"\x1aE\xdf\xa3"


def assert_api_error(res: Any, status: int, code: str, data_dir: Path) -> None:
    assert res.status_code == status
    body = res.json()
    assert set(body) <= {"code", "message", "lessonId"}
    assert body["code"] == code
    assert str(data_dir) not in res.text
    assert "ffmpeg" not in res.text.lower()
    assert tmp_files(data_dir) == []


def test_m3u8_playlist_is_415_and_ffmpeg_never_runs(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_kw: object) -> None:
        raise AssertionError("ffmpeg must not run for an unsniffable upload")

    monkeypatch.setattr(subprocess, "run", boom)
    playlist = b"#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:1,\nfile:///etc/hosts\n"

    res = post(client, playlist, filename="rec.webm")

    assert_api_error(res, 415, "unsupported_media", data_dir)


def test_empty_upload_is_415(client: TestClient, data_dir: Path) -> None:
    assert_api_error(post(client, b""), 415, "unsupported_media", data_dir)


def test_plain_wav_is_415(client: TestClient, data_dir: Path, tmp_path: Path) -> None:
    wav = tmp_path / "plain.wav"
    sf.write(wav, voice_like(), SR, subtype="PCM_16")

    res = post(client, wav.read_bytes(), filename="rec.wav")

    assert_api_error(res, 415, "unsupported_media", data_dir)


def test_webm_magic_with_garbage_body_is_415_without_stderr(
    client: TestClient, data_dir: Path
) -> None:
    res = post(client, WEBM_MAGIC + b"\x00garbage" * 200)

    assert_api_error(res, 415, "unsupported_media", data_dir)


def test_body_over_10_mb_is_413(client: TestClient, data_dir: Path) -> None:
    res = post(client, WEBM_MAGIC + b"\x00" * (MAX_BYTES + 1024))

    assert_api_error(res, 413, "payload_too_large", data_dir)


def test_chunked_body_over_10_mb_is_413_while_streaming(client: TestClient, data_dir: Path) -> None:
    boundary = "x-boundary"
    head = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="rec.webm"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body() -> Iterator[bytes]:
        yield head + WEBM_MAGIC
        for _ in range(MAX_BYTES // 65536 + 2):
            yield b"\x00" * 65536
        yield tail

    res = client.post(
        f"/lessons/{LESSON_ID}/segments/0/attempts",
        content=body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )

    assert_api_error(res, 413, "payload_too_large", data_dir)


def test_recording_longer_than_60_s_is_422(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    res = post(client, webm(silence(65.0), tmp_path, "long.webm"))

    assert_api_error(res, 422, "recording_too_long", data_dir)


def test_failed_uploads_do_not_create_an_attempt(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    post(client, b"")
    post(client, webm(silence(65.0), tmp_path, "long.webm"))

    ok = post(client, webm(voice_like(), tmp_path))

    assert ok.json()["attempt"] == 1


def test_very_short_recording_normalizes_and_is_not_voiced(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    res = post(client, webm(voice_like(0.2), tmp_path, "short.webm"))

    assert res.status_code == 201
    assert res.json()["voiced"] is False
    assert res.json()["durationMs"] <= 260
    assert tmp_files(data_dir) == []


# --- Task 3: "Lưu clip cho eval" (D-09, 02-01 mục D) -------------------------------------------


def clip_files(data_dir: Path) -> list[Path]:
    root = data_dir / "eval_clips"
    return sorted(root.iterdir()) if root.exists() else []


def put_eval_clip(
    client: TestClient,
    body: bytes,
    *,
    lesson_id: str = LESSON_ID,
    index: int = 0,
    attempt: int = 1,
) -> Any:
    return client.put(
        f"/lessons/{lesson_id}/segments/{index}/attempts/{attempt}/eval-clip",
        files={"audio": ("rec.webm", body, "application/octet-stream")},
    )


def saved_flag(lesson_id: str, index: int, attempt: int) -> bool:
    row = db.get_attempt(lesson_id, index, attempt)
    assert row is not None
    return row.saved_for_eval


def test_save_for_eval_on_upload_stores_clip_and_sidecar(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    res = post(client, webm(voice_like(), tmp_path), save=True)

    assert res.status_code == 201
    assert res.json()["savedForEval"] is True
    wav = data_dir / "eval_clips" / f"{LESSON_ID}_0000_01.wav"
    sidecar = wav.with_suffix(".json")
    assert [p.name for p in clip_files(data_dir)] == [sidecar.name, wav.name]
    info = sf.info(wav)
    assert (info.samplerate, info.channels) == (16000, 1)
    assert json.loads(sidecar.read_text(encoding="utf-8")) == {
        "lessonId": LESSON_ID,
        "segmentIndex": 0,
        "attempt": 1,
        "text": "Sentence 0",
    }
    assert saved_flag(LESSON_ID, 0, 1) is True
    assert tmp_files(data_dir) == []


def test_upload_without_save_for_eval_leaves_no_clip(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    for save in (None, False):
        res = post(client, webm(voice_like(), tmp_path), save=save)
        assert res.json()["savedForEval"] is False

    assert clip_files(data_dir) == []
    assert saved_flag(LESSON_ID, 0, 1) is False


def test_put_eval_clip_stores_the_blob_without_a_new_attempt(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    blob = webm(voice_like(), tmp_path)
    first = post(client, blob)
    assert first.json()["savedForEval"] is False
    assert clip_files(data_dir) == []

    res = put_eval_clip(client, blob)

    assert res.status_code == 200
    body = res.json()
    assert body["savedForEval"] is True
    assert body["attempt"] == 1
    assert body["lessonId"] == LESSON_ID
    assert body["segmentIndex"] == 0
    assert body["voiced"] == first.json()["voiced"]
    assert body["durationMs"] == first.json()["durationMs"]
    assert (data_dir / "eval_clips" / f"{LESSON_ID}_0000_01.wav").is_file()
    assert saved_flag(LESSON_ID, 0, 1) is True
    assert db.get_attempt(LESSON_ID, 0, 2) is None  # PUT không tạo lượt mới
    assert [r.attempts for r in db.segment_progress(LESSON_ID)] == [1]
    assert tmp_files(data_dir) == []


def test_put_eval_clip_for_missing_attempt_is_404_not_found(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    res = put_eval_clip(client, webm(voice_like(), tmp_path), attempt=9)

    assert_api_error(res, 404, "not_found", data_dir)
    assert clip_files(data_dir) == []


def test_put_eval_clip_on_not_ready_lesson_is_409(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    res = put_eval_clip(client, webm(voice_like(), tmp_path), lesson_id=QUEUED_ID)

    assert_api_error(res, 409, "invalid_state", data_dir)


def test_put_eval_clip_rejects_bad_segment_and_bad_media(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    post(client, webm(voice_like(), tmp_path))

    out_of_range = put_eval_clip(client, webm(voice_like(), tmp_path), index=5)
    garbage = put_eval_clip(client, b"#EXTM3U\nfile:///etc/hosts\n")

    assert_api_error(out_of_range, 404, "invalid_segment", data_dir)
    assert_api_error(garbage, 415, "unsupported_media", data_dir)
    assert clip_files(data_dir) == []
    assert saved_flag(LESSON_ID, 0, 1) is False

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from audio_service.config import get_settings, lesson_json_path
from audio_service.main import create_app

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"


def make_lesson(lesson_id: str = LESSON_ID) -> dict[str, Any]:
    return {
        "id": lesson_id,
        "videoId": "dUDi-F6eAvk",
        "title": "Demo",
        "durationSec": 12.5,
        "range": {"start": 0.0, "end": 12.5},
        "padMs": 150,
        "status": "ready",
        "segments": [
            {
                "index": 0,
                "text": "Hello world",
                "start": 0.5,
                "end": 1.75,
                "endExtraMs": 0,
                "words": [
                    {"i": 0, "text": "Hello", "start": 0.5, "end": 1.0, "asrProb": 0.98},
                    {
                        "i": 1,
                        "text": "world",
                        "start": 1.0,
                        "end": 1.75,
                        "asrProb": 0.91,
                        "prominence": 0.4,
                    },
                ],
            }
        ],
        "createdAt": "2026-10-06T08:00:00.000Z",
    }


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def store(lesson: dict[str, Any]) -> Path:
    path = lesson_json_path(lesson["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson), encoding="utf-8")
    return path


def test_get_lesson_returns_stored_camel_case_json(client: TestClient) -> None:
    lesson = make_lesson()
    store(lesson)
    res = client.get(f"/lessons/{LESSON_ID}")
    assert res.status_code == 200
    assert res.json() == lesson  # camelCase, optional vắng mặt vẫn vắng mặt


@pytest.mark.parametrize(
    "bad_id",
    ["abc", "01hzx3y7q8k2m4n6p8r0s2t4v6", "..%2Fetc", "%2e%2e%2f%2e%2e%2fetc%2fpasswd"],
)
def test_bad_ids_return_404(client: TestClient, bad_id: str) -> None:
    assert client.get(f"/lessons/{bad_id}").status_code == 404


def test_unknown_ulid_returns_404(client: TestClient) -> None:
    assert client.get(f"/lessons/{LESSON_ID}").status_code == 404


def test_corrupt_file_returns_500_without_path(client: TestClient, data_dir: Path) -> None:
    path = lesson_json_path(LESSON_ID)
    path.parent.mkdir(parents=True)
    path.write_text('{"id": "x"}', encoding="utf-8")
    res = client.get(f"/lessons/{LESSON_ID}")
    assert res.status_code == 500
    assert str(data_dir) not in res.text


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "audio", "version": "0.1.0"}


def test_cors_allows_only_localhost_3000(client: TestClient) -> None:
    allowed = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    denied = client.options(
        "/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers
    simple = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_scoring_router_is_empty_and_mounted(client: TestClient) -> None:
    from audio_service.routers import scoring

    assert scoring.router.prefix == "/scoring"
    assert scoring.router.routes == []
    assert not [p for p in client.app.openapi()["paths"] if p.startswith("/scoring")]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH"])
def test_cors_preflight_allows_write_methods_only_from_localhost_3000(
    client: TestClient, method: str
) -> None:
    allowed = client.options(
        "/lessons",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert method in allowed.headers.get("access-control-allow-methods", "")
    denied = client.options(
        "/lessons",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": method},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_cors_does_not_allow_delete(client: TestClient) -> None:
    res = client.options(
        "/lessons",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "DELETE"},
    )
    assert "DELETE" not in res.headers.get("access-control-allow-methods", "")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_write_with_foreign_origin_is_403_forbidden_origin(client: TestClient, method: str) -> None:
    res = client.request(
        method,
        "/lessons",
        json={"url": "https://www.youtube.com/watch?v=dUDi-F6eAvk"},
        headers={"Origin": "http://evil.example"},
    )
    assert res.status_code == 403
    assert res.json() == {
        "code": "forbidden_origin",
        "message": "Yêu cầu không đến từ app ShadowEngLab.",
    }


def test_multipart_post_with_foreign_origin_is_blocked(client: TestClient) -> None:
    # Pitfall 7: multipart POST là "simple request" nên CORS preflight không chặn được.
    res = client.post(
        "/lessons",
        files={"audio": ("a.webm", b"x", "audio/webm")},
        headers={"Origin": "null"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "forbidden_origin"


def test_write_from_the_web_app_origin_passes_the_guard(client: TestClient) -> None:
    res = client.post("/lessons", json={}, headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 422  # qua guard, dừng ở validate


def test_write_without_origin_is_not_blocked_by_the_guard(client: TestClient) -> None:
    res = client.post("/lessons", json={})  # script / curl / TestClient không gửi Origin
    assert res.status_code == 422


def test_read_with_foreign_origin_is_not_blocked_by_the_guard(client: TestClient) -> None:
    res = client.get("/health", headers={"Origin": "http://evil.example"})
    assert res.status_code == 200


def test_host_header_other_than_loopback_is_rejected(data_dir: Path) -> None:
    app = create_app()
    with TestClient(app, base_url="http://evil.example") as evil:
        assert evil.get("/health").status_code == 400
    with TestClient(app, base_url="http://localhost") as local:
        assert local.get("/health").status_code == 200
    with TestClient(app, base_url="http://127.0.0.1") as loopback:
        assert loopback.get("/health").status_code == 200


def test_empty_body_is_422_invalid_request_without_pydantic_text(client: TestClient) -> None:
    res = client.post("/lessons", json={})
    assert res.status_code == 422
    assert res.json() == {"code": "invalid_request", "message": "Dữ liệu gửi lên không hợp lệ."}
    assert "pydantic" not in res.text and "Field required" not in res.text


def test_validation_error_does_not_echo_the_input(client: TestClient) -> None:
    res = client.post("/lessons", json={"url": 12345, "secret": "hunter2"})
    assert res.status_code == 422
    assert "hunter2" not in res.text and "12345" not in res.text
    assert res.json()["code"] == "invalid_request"

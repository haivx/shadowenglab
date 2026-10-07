import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from audio_service import db
from audio_service.config import app_db_path, get_settings, lesson_json_path
from audio_service.main import create_app

READY_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
FAILED_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V7"
EMPTY_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V8"


def make_segment(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "text": f"Sentence {index}",
        "start": float(index),
        "end": float(index) + 0.9,
        "endExtraMs": 0,
        "words": [
            {
                "i": 0,
                "text": "Sentence",
                "start": float(index),
                "end": float(index) + 0.9,
                "asrProb": 0.95,
            }
        ],
    }


def make_lesson(
    lesson_id: str,
    *,
    created_at: str,
    status: str = "ready",
    segments: int = 3,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": lesson_id,
        "videoId": "dUDi-F6eAvk",
        "title": f"Lesson {lesson_id[-2:]}",
        "durationSec": 12.5,
        "range": {"start": 0.0, "end": 12.5},
        "padMs": 150,
        "status": status,
        "segments": [make_segment(i) for i in range(segments)],
        "createdAt": created_at,
        **extra,
    }


def store(lesson: dict[str, Any]) -> Path:
    path = lesson_json_path(lesson["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lesson), encoding="utf-8")
    return path


def contains_null(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, dict):
        return any(contains_null(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_null(v) for v in value)
    return False


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def test_list_is_empty_when_no_lessons(client: TestClient) -> None:
    res = client.get("/lessons")
    assert res.status_code == 200
    assert res.json() == []


def test_list_orders_newest_first_with_practice_counts(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    store(
        make_lesson(
            FAILED_ID,
            created_at="2026-10-07T08:00:00.000Z",
            status="failed",
            segments=0,
            error={"step": "downloading", "message": "mạng lỗi"},
        )
    )
    db.insert_attempt(READY_ID, 0, duration_ms=1200, voiced=True)
    db.insert_attempt(READY_ID, 0, duration_ms=1100, voiced=True)  # cùng câu: vẫn tính 1 câu
    db.insert_attempt(READY_ID, 1, duration_ms=300, voiced=False)  # không voiced: chưa tính

    res = client.get("/lessons")
    assert res.status_code == 200
    items = res.json()
    assert [item["lesson"]["id"] for item in items] == [FAILED_ID, READY_ID]

    failed, ready = items
    assert failed["segmentCount"] == 0
    assert failed["practicedCount"] == 0
    assert failed["firstUnpracticedIndex"] is None
    assert failed["lesson"]["error"] == {"step": "downloading", "message": "mạng lỗi"}

    assert ready["segmentCount"] == 3
    assert ready["practicedCount"] == 1
    assert ready["firstUnpracticedIndex"] == 1
    assert ready["lesson"]["title"] == "Lesson V6"


def test_list_items_are_light_and_omit_absent_optionals(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    items = client.get("/lessons").json()
    lesson = items[0]["lesson"]
    assert "segments" not in lesson
    assert "error" not in lesson
    assert "audioQuality" not in lesson
    assert "thumbnailUrl" not in lesson
    # firstUnpracticedIndex là null có chủ đích ở các bài đã tập hết; ngoài ra không có null nào.
    assert not contains_null({"lesson": lesson})


def test_audio_quality_passes_through_when_present(client: TestClient) -> None:
    quality = {"label": "music", "nonVocalRatio": 0.42}
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z", audioQuality=quality))
    item = client.get("/lessons").json()[0]
    assert item["lesson"]["audioQuality"] == quality


def test_every_sentence_practiced_gives_null_first_index(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z", segments=2))
    for index in (0, 1):
        db.insert_attempt(READY_ID, index, duration_ms=900, voiced=True)
    item = client.get("/lessons").json()[0]
    assert item["practicedCount"] == 2
    assert item["firstUnpracticedIndex"] is None


def test_no_attempts_gives_first_index_zero(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    item = client.get("/lessons").json()[0]
    assert item["practicedCount"] == 0
    assert item["firstUnpracticedIndex"] == 0


def test_attempts_beyond_segment_count_are_ignored(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z", segments=2))
    db.insert_attempt(READY_ID, 5, duration_ms=900, voiced=True)
    item = client.get("/lessons").json()[0]
    assert item["practicedCount"] == 0
    assert item["firstUnpracticedIndex"] == 0


def test_corrupt_lesson_json_is_skipped_not_500(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    bad = lesson_json_path(EMPTY_ID)
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{not json", encoding="utf-8")
    res = client.get("/lessons")
    assert res.status_code == 200
    assert [item["lesson"]["id"] for item in res.json()] == [READY_ID]


def test_attempts_db_has_only_the_approved_schema(client: TestClient) -> None:
    db.insert_attempt(READY_ID, 0, duration_ms=900, voiced=True)
    with db.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        objects = conn.execute(
            "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(attempts)")]
    assert [(row["type"], row["name"]) for row in objects] == [("table", "attempts")]
    assert columns == [
        "lesson_id",
        "segment_index",
        "attempt",
        "created_at",
        "duration_ms",
        "voiced",
        "saved_for_eval",
    ]
    assert app_db_path().is_file()


def test_bad_lesson_id_never_reaches_sql(data_dir: Path) -> None:
    with pytest.raises(ValueError):
        db.practiced_indexes(["x'; DROP TABLE attempts; --"])
    with pytest.raises(ValueError):
        db.insert_attempt("../x", 0, duration_ms=1, voiced=True)


@pytest.mark.parametrize(
    ("count", "practiced", "expected"),
    [(0, set(), None), (3, set(), 0), (3, {0, 1}, 2), (3, {0, 1, 2}, None), (1, {0}, None)],
)
def test_first_unpracticed_index(count: int, practiced: set[int], expected: int | None) -> None:
    assert db.first_unpracticed_index(count, practiced) == expected


# --- GET /lessons/{id}/progress (02-06 Task 2) ---------------------------------------------


def test_progress_lists_only_attempted_segments(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    db.insert_attempt(READY_ID, 0, duration_ms=1000, voiced=True)
    db.insert_attempt(READY_ID, 0, duration_ms=100, voiced=False)
    db.insert_attempt(READY_ID, 1, duration_ms=100, voiced=False)
    res = client.get(f"/lessons/{READY_ID}/progress")
    assert res.status_code == 200
    assert res.json() == {
        "lessonId": READY_ID,
        "segments": [
            {"segmentIndex": 0, "attempts": 2, "voicedAttempts": 1},
            {"segmentIndex": 1, "attempts": 1, "voicedAttempts": 0},
        ],
        "firstUnpracticedIndex": 1,
    }


def test_progress_without_attempts_opens_at_zero(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z"))
    body = client.get(f"/lessons/{READY_ID}/progress").json()
    assert body == {"lessonId": READY_ID, "segments": [], "firstUnpracticedIndex": 0}


def test_progress_all_practiced_gives_null(client: TestClient) -> None:
    store(make_lesson(READY_ID, created_at="2026-10-06T08:00:00.000Z", segments=2))
    for index in (0, 1):
        db.insert_attempt(READY_ID, index, duration_ms=1000, voiced=True)
    assert client.get(f"/lessons/{READY_ID}/progress").json()["firstUnpracticedIndex"] is None


def test_progress_of_lesson_not_ready_has_null_first_index(client: TestClient) -> None:
    store(
        make_lesson(FAILED_ID, created_at="2026-10-06T08:00:00.000Z", status="queued", segments=0)
    )
    body = client.get(f"/lessons/{FAILED_ID}/progress").json()
    assert body == {"lessonId": FAILED_ID, "segments": [], "firstUnpracticedIndex": None}


@pytest.mark.parametrize("bad_id", [EMPTY_ID, "abc", "01hzx3y7q8k2m4n6p8r0s2t4v6"])
def test_progress_unknown_or_malformed_id_is_404_api_error(client: TestClient, bad_id: str) -> None:
    res = client.get(f"/lessons/{bad_id}/progress")
    assert res.status_code == 404
    assert res.json() == {"code": "not_found", "message": "Không tìm thấy bài."}


@pytest.mark.parametrize("bad_id", ["..%2Fetc", "%2e%2e%2fpasswd"])
def test_progress_traversal_ids_are_404(client: TestClient, bad_id: str) -> None:
    # Có thể không khớp route (khi %2F được giải mã thành dấu /): chỉ yêu cầu 404, không lộ file.
    res = client.get(f"/lessons/{bad_id}/progress")
    assert res.status_code == 404
    assert "root:" not in res.text


def test_progress_of_unreadable_lesson_json_is_404(client: TestClient) -> None:
    path = lesson_json_path(EMPTY_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert client.get(f"/lessons/{EMPTY_ID}/progress").status_code == 404

import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from audio_service import db
from audio_service.config import InvalidIdError, app_db_path, get_settings

LESSON = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


def test_insert_attempt_numbers_per_lesson_and_segment(data_dir: Path) -> None:
    first = [db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True) for _ in range(3)]
    assert first == [1, 2, 3]
    assert db.insert_attempt(LESSON, 1, duration_ms=1000, voiced=True) == 1


def test_non_voiced_uploads_take_a_number_too(data_dir: Path) -> None:
    assert db.insert_attempt(LESSON, 0, duration_ms=200, voiced=False) == 1
    assert db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True) == 2


def test_concurrent_inserts_get_distinct_numbers(data_dir: Path) -> None:
    results: list[int] = []
    errors: list[BaseException] = []
    guard = threading.Lock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(5):
                number = db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
                with guard:
                    results.append(number)
        except BaseException as exc:  # noqa: BLE001 - gom lỗi từ thread để assert ở main
            with guard:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert sorted(results) == list(range(1, 41))


def test_mark_saved_for_eval_sets_flag_and_reports_unknown(data_dir: Path) -> None:
    for _ in range(2):
        db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    assert db.mark_saved_for_eval(LESSON, 0, 2) is True
    row = db.get_attempt(LESSON, 0, 2)
    assert row is not None and row.saved_for_eval is True
    other = db.get_attempt(LESSON, 0, 1)
    assert other is not None and other.saved_for_eval is False
    assert db.mark_saved_for_eval(LESSON, 0, 9) is False
    assert db.mark_saved_for_eval(LESSON, 7, 1) is False


def test_mark_saved_for_eval_is_idempotent(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    assert db.mark_saved_for_eval(LESSON, 0, 1) is True
    assert db.mark_saved_for_eval(LESSON, 0, 1) is True


def test_get_attempt_returns_row_fields_or_none(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 3, duration_ms=1234, voiced=False, saved_for_eval=True)
    row = db.get_attempt(LESSON, 3, 1)
    assert row == db.AttemptRow(
        lesson_id=LESSON,
        segment_index=3,
        attempt=1,
        created_at=row.created_at if row else "",
        duration_ms=1234,
        voiced=False,
        saved_for_eval=True,
    )
    assert row is not None and row.created_at.endswith("Z") and "T" in row.created_at
    assert db.get_attempt(LESSON, 3, 2) is None
    assert db.get_attempt(LESSON, 4, 1) is None


def test_segment_progress_counts_all_and_voiced_only_for_attempted_segments(
    data_dir: Path,
) -> None:
    db.insert_attempt(LESSON, 2, duration_ms=1000, voiced=True)
    db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    db.insert_attempt(LESSON, 0, duration_ms=100, voiced=False)
    db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    assert db.segment_progress(LESSON) == [
        db.SegmentProgressRow(segment_index=0, attempts=3, voiced_attempts=2),
        db.SegmentProgressRow(segment_index=2, attempts=1, voiced_attempts=1),
    ]


def test_segment_progress_is_empty_without_attempts_and_scoped_to_lesson(data_dir: Path) -> None:
    assert db.segment_progress(LESSON) == []
    db.insert_attempt("01HZX3Y7Q8K2M4N6P8R0S2T4V7", 0, duration_ms=1000, voiced=True)
    assert db.segment_progress(LESSON) == []


def test_functions_reject_bad_lesson_ids(data_dir: Path) -> None:
    for bad in ("../x", "abc", "x'; DROP TABLE attempts; --"):
        with pytest.raises(InvalidIdError):
            db.segment_progress(bad)
        with pytest.raises(InvalidIdError):
            db.get_attempt(bad, 0, 1)
        with pytest.raises(InvalidIdError):
            db.mark_saved_for_eval(bad, 0, 1)


def test_ensure_schema_on_existing_v1_db_is_a_noop(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    conn = sqlite3.connect(app_db_path())
    try:
        db.ensure_schema(conn)
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    finally:
        conn.close()


def test_check_constraints_reject_bad_rows(data_dir: Path) -> None:
    with pytest.raises(ValueError):
        db.insert_attempt(LESSON, -1, duration_ms=1, voiced=True)
    with db.connection() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO attempts VALUES (?, 0, 0, '2026-01-01T00:00:00.000Z', 1, 1, 0)",
                (LESSON,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO attempts VALUES (?, 0, 1, '2026-01-01T00:00:00.000Z', 1, 2, 0)",
                (LESSON,),
            )

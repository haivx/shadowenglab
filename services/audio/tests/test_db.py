import json
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from audio_service import db
from audio_service.config import InvalidIdError, app_db_path, get_settings
from audio_service.contracts_gen import ScoreResult

LESSON = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
FIXTURES = Path(__file__).resolve().parents[3] / "packages/contracts/fixtures"
V2_COLUMNS = ["overall", "intonation", "rhythm", "sound", "result_json"]


def result_for(attempt: int, overall: float) -> ScoreResult:
    """ScoreResult hợp lệ từ fixture của contract, đổi số lượt và overall."""
    fixture = json.loads((FIXTURES / "ScoreResult.json").read_text(encoding="utf-8"))
    payload: dict[str, Any] = next(c["data"] for c in fixture if c["name"] == "full")
    payload = {
        **payload,
        "lessonId": LESSON,
        "segmentIndex": 0,
        "attempt": attempt,
        "scores": {**payload["scores"], "overall": overall},
    }
    return ScoreResult.model_validate(payload)


def score(segment: int, overall: float) -> ScoreResult:
    return db.insert_scored_attempt(
        LESSON, segment, duration_ms=1500, build=lambda n: result_for(n, overall)
    )


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


def make_v1_database() -> None:
    """Dựng đúng DB của Phase 2 (DDL v1, user_version 1) với hai dòng P1."""
    path = app_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(db._DDL)
        conn.executemany(
            "INSERT INTO attempts VALUES (?, 0, ?, '2026-10-01T00:00:00.000Z', 1500, 1, 0)",
            [(LESSON, 1), (LESSON, 2)],
        )
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    finally:
        conn.close()


def test_v1_database_migrates_to_v2_keeping_rows_and_is_a_noop_afterwards(data_dir: Path) -> None:
    make_v1_database()
    conn = sqlite3.connect(app_db_path())
    try:
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        columns = [row[1] for row in conn.execute("PRAGMA table_info(attempts)")]
        assert columns[-5:] == V2_COLUMNS
        rows = conn.execute(
            "SELECT attempt, voiced, overall, intonation, rhythm, sound, result_json "
            "FROM attempts ORDER BY attempt"
        ).fetchall()
        assert rows == [(1, 1, None, None, None, None, None), (2, 1, None, None, None, None, None)]

        db.ensure_schema(conn)  # chạy lại: không đổi gì, không lỗi "duplicate column"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 2
    finally:
        conn.close()


def test_migrated_database_keeps_numbering_and_stores_scores(data_dir: Path) -> None:
    make_v1_database()
    stored = score(0, 0.81)
    assert stored.attempt == 3  # tiếp theo hai lượt P1
    assert [(r.attempt, r.overall) for r in db.list_scored_attempts(LESSON, 0)] == [(3, 0.81)]


def test_fresh_database_reaches_v2(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 0, duration_ms=1000, voiced=True)
    with db.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(attempts)")]
    assert columns[-5:] == V2_COLUMNS


def test_check_constraints_reject_bad_rows(data_dir: Path) -> None:
    with pytest.raises(ValueError):
        db.insert_attempt(LESSON, -1, duration_ms=1, voiced=True)
    base = (
        "INSERT INTO attempts (lesson_id, segment_index, attempt, created_at, duration_ms, voiced"
    )
    with db.connection() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"{base}) VALUES (?, 0, 0, '2026-01-01T00:00:00.000Z', 1, 1)",
                (LESSON,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"{base}) VALUES (?, 0, 1, '2026-01-01T00:00:00.000Z', 1, 2)",
                (LESSON,),
            )
        for column in ("overall", "intonation", "rhythm", "sound"):
            for bad in (1.5, -0.1):
                with pytest.raises(sqlite3.IntegrityError):
                    conn.execute(
                        f"{base}, {column}) VALUES (?, 0, 1, '2026-01-01T00:00:00.000Z', 1, 1, ?)",
                        (LESSON, bad),
                    )


def test_insert_scored_attempt_stores_scores_and_validated_json(data_dir: Path) -> None:
    result = score(0, 0.74)
    assert result.attempt == 1
    with db.connection() as conn:
        row = conn.execute(
            "SELECT voiced, overall, intonation, rhythm, sound, result_json FROM attempts"
        ).fetchone()
    assert row["voiced"] == 1
    assert (row["overall"], row["intonation"], row["rhythm"], row["sound"]) == (
        0.74,
        result.scores.intonation,
        result.scores.rhythm,
        result.scores.sound,
    )
    assert ScoreResult.model_validate_json(row["result_json"]) == result
    assert db.get_attempt_result_json(LESSON, 0, 1) == row["result_json"]


def test_insert_scored_attempt_rolls_back_when_build_fails(data_dir: Path) -> None:
    def boom(_attempt: int) -> ScoreResult:
        raise RuntimeError("scoring failed")

    with pytest.raises(RuntimeError):
        db.insert_scored_attempt(LESSON, 0, duration_ms=1, build=boom)
    assert db.segment_progress(LESSON) == []
    assert score(0, 0.5).attempt == 1  # số lượt không bị tiêu hao


def test_concurrent_scored_inserts_get_distinct_numbers(data_dir: Path) -> None:
    numbers: list[int] = []
    errors: list[BaseException] = []
    guard = threading.Lock()
    barrier = threading.Barrier(6)

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(3):
                attempt = score(0, 0.5).attempt
                with guard:
                    numbers.append(attempt)
        except BaseException as exc:  # noqa: BLE001 - gom lỗi từ thread để assert ở main
            with guard:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert sorted(numbers) == list(range(1, 19))


def test_best_attempt_is_highest_overall_and_later_wins_ties(data_dir: Path) -> None:
    for overall in (0.70, 0.78, 0.78):
        score(0, overall)
    score(1, 0.6)
    score(1, 0.4)  # lượt sau thấp hơn: điểm tốt nhất không bị mất (FBK-06, D-11)
    db.insert_attempt(LESSON, 2, duration_ms=900, voiced=True)  # chỉ có lượt P1: không có best

    progress = {row.segment_index: row for row in db.segment_progress(LESSON)}

    assert (progress[0].best_overall, progress[0].best_attempt) == (0.78, 3)
    assert (progress[0].attempts, progress[0].voiced_attempts) == (3, 3)
    assert (progress[1].best_overall, progress[1].best_attempt) == (0.6, 1)
    assert (progress[2].best_overall, progress[2].best_attempt) == (None, None)


def test_list_scored_attempts_excludes_unscored_rows_in_ascending_order(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 0, duration_ms=100, voiced=False)  # no_speech / P1
    score(0, 0.5)
    db.insert_attempt(LESSON, 0, duration_ms=900, voiced=True)  # P1 voiced không điểm
    score(0, 0.9)

    rows = db.list_scored_attempts(LESSON, 0)

    assert [(r.attempt, r.overall) for r in rows] == [(2, 0.5), (4, 0.9)]
    assert all(r.created_at.endswith("Z") for r in rows)
    assert db.list_scored_attempts(LESSON, 1) == []


def test_get_attempt_result_json_is_none_for_unscored_or_missing(data_dir: Path) -> None:
    db.insert_attempt(LESSON, 0, duration_ms=100, voiced=False)
    assert db.get_attempt_result_json(LESSON, 0, 1) is None
    assert db.get_attempt_result_json(LESSON, 0, 9) is None


def test_scored_functions_reject_bad_lesson_ids(data_dir: Path) -> None:
    for bad in ("../x", "abc", "x'; DROP TABLE attempts; --"):
        with pytest.raises(InvalidIdError):
            db.list_scored_attempts(bad, 0)
        with pytest.raises(InvalidIdError):
            db.get_attempt_result_json(bad, 0, 1)
        with pytest.raises(InvalidIdError):
            db.insert_scored_attempt(bad, 0, duration_ms=1, build=lambda n: result_for(n, 0.5))

"""SQLite `DATA_DIR/app.db`: bảng `attempts` (D-02, 02-01 mục B/C).

Chỉ có một bảng `attempts`. user_version 1 là DDL của Phase 2; user_version 2 (Phase 3, D-10)
thêm các cột điểm và `result_json` bằng ALTER, giữ nguyên các dòng cũ (điểm NULL).
Mỗi lời gọi mở một connection riêng rồi đóng (Pitfall 13: không chia sẻ connection giữa thread).
Mọi câu SQL dùng tham số `?`, id bài được kiểm bằng ULID_RE trước khi chạm DB (T-02-14).
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from audio_service.config import ULID_RE, InvalidIdError, _check_id, app_db_path
from audio_service.contracts_gen import ScoreResult

SCHEMA_VERSION = 2

_DDL = """
CREATE TABLE IF NOT EXISTS attempts (
    lesson_id TEXT NOT NULL,
    segment_index INTEGER NOT NULL CHECK (segment_index >= 0),
    attempt INTEGER NOT NULL CHECK (attempt >= 1),
    created_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    voiced INTEGER NOT NULL CHECK (voiced IN (0, 1)),
    saved_for_eval INTEGER NOT NULL DEFAULT 0 CHECK (saved_for_eval IN (0, 1)),
    PRIMARY KEY (lesson_id, segment_index, attempt)
)
"""

# user_version 1 -> 2 (D-10, 03-01 mục B). Điểm trong [0, 1]; `result_json` là ScoreResult đầy đủ.
_SCORE_CHECK = "CHECK ({col} IS NULL OR ({col} >= 0 AND {col} <= 1))"
_V2_ALTERS = (
    *(
        f"ALTER TABLE attempts ADD COLUMN {col} REAL {_SCORE_CHECK.format(col=col)}"
        for col in ("overall", "intonation", "rhythm", "sound")
    ),
    "ALTER TABLE attempts ADD COLUMN result_json TEXT",
)

# SQLite cũ giới hạn 999 tham số mỗi câu lệnh.
_IN_CHUNK = 500

_SCHEMA_READY: set[Path] = set()
_SCHEMA_GUARD = threading.Lock()


@dataclass(frozen=True)
class AttemptRow:
    lesson_id: str
    segment_index: int
    attempt: int
    created_at: str
    duration_ms: int
    voiced: bool
    saved_for_eval: bool


@dataclass(frozen=True)
class SegmentProgressRow:
    segment_index: int
    attempts: int
    voiced_attempts: int


def _now_iso() -> str:
    """Cùng dạng với `pipeline._now_iso` và JS `toISOString()`."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: user_version 0 -> DDL v1 + ALTER v2; 1 -> chỉ ALTER v2; kết quả là v2."""
    if conn.execute("PRAGMA user_version").fetchone()[0] >= SCHEMA_VERSION:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Kiểm lại sau khi giữ khoá ghi: tiến trình khác có thể vừa migrate xong.
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            conn.execute(_DDL)
        if version < 2:
            for statement in _V2_ALTERS:
                conn.execute(statement)
        if version < SCHEMA_VERSION:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    """Một connection cho mỗi lời gọi (autocommit; transaction tự quản bằng BEGIN)."""
    path = app_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        with _SCHEMA_GUARD:
            if path not in _SCHEMA_READY:
                ensure_schema(conn)
                _SCHEMA_READY.add(path)
        yield conn
    finally:
        conn.close()


def _check_lesson_id(lesson_id: str) -> str:
    return _check_id(lesson_id, ULID_RE, "lesson id")


def practiced_indexes(lesson_ids: Sequence[str]) -> dict[str, set[int]]:
    """Mỗi bài: các segment_index có >= 1 lượt voiced (D-08). Mọi id đều có mặt trong kết quả."""
    ids = [_check_lesson_id(lesson_id) for lesson_id in lesson_ids]
    result: dict[str, set[int]] = {lesson_id: set() for lesson_id in ids}
    if not ids:
        return result
    with connection() as conn:
        for start in range(0, len(ids), _IN_CHUNK):
            chunk = ids[start : start + _IN_CHUNK]
            marks = ",".join("?" * len(chunk))  # chỉ sinh dấu ?, không ghép giá trị vào SQL
            rows = conn.execute(
                "SELECT DISTINCT lesson_id, segment_index FROM attempts "
                f"WHERE voiced = 1 AND lesson_id IN ({marks})",
                chunk,
            )
            for row in rows:
                result[row["lesson_id"]].add(row["segment_index"])
    return result


def first_unpracticed_index(segment_count: int, practiced: set[int]) -> int | None:
    """Câu đầu tiên chưa tập; None khi không có câu nào hoặc đã tập hết."""
    for index in range(segment_count):
        if index not in practiced:
            return index
    return None


def insert_attempt(
    lesson_id: str,
    segment_index: int,
    *,
    duration_ms: int,
    voiced: bool,
    saved_for_eval: bool = False,
) -> int:
    """Ghi một lượt, trả số lượt (1, 2, 3...) theo (bài, câu); lượt không voiced cũng tính."""
    _check_lesson_id(lesson_id)
    if segment_index < 0:
        raise InvalidIdError("invalid segment index")
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")  # khoá ghi trước khi đọc MAX: hai thread không trùng số
        try:
            attempt = conn.execute(
                "SELECT COALESCE(MAX(attempt), 0) + 1 FROM attempts "
                "WHERE lesson_id = ? AND segment_index = ?",
                (lesson_id, segment_index),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO attempts (lesson_id, segment_index, attempt, created_at, "
                "duration_ms, voiced, saved_for_eval) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    lesson_id,
                    segment_index,
                    attempt,
                    _now_iso(),
                    duration_ms,
                    int(voiced),
                    int(saved_for_eval),
                ),
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return int(attempt)


def insert_scored_attempt(
    lesson_id: str,
    segment_index: int,
    *,
    duration_ms: int,
    build: Callable[[int], ScoreResult],
) -> ScoreResult:
    """Đánh số lượt rồi ghi điểm + ScoreResult trong MỘT transaction (C1, D-09/D-10).

    `build(attempt)` dựng ScoreResult với đúng số lượt vừa cấp; nó (hoặc INSERT) lỗi thì ROLLBACK,
    không dòng nào được ghi. `result_json` ở dạng camelCase của contract, bỏ field chưa đặt.
    """
    _check_lesson_id(lesson_id)
    if segment_index < 0:
        raise InvalidIdError("invalid segment index")
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")  # khoá ghi trước khi đọc MAX: hai thread không trùng số
        try:
            attempt = int(
                conn.execute(
                    "SELECT COALESCE(MAX(attempt), 0) + 1 FROM attempts "
                    "WHERE lesson_id = ? AND segment_index = ?",
                    (lesson_id, segment_index),
                ).fetchone()[0]
            )
            result = build(attempt)
            scores = result.scores
            conn.execute(
                "INSERT INTO attempts (lesson_id, segment_index, attempt, created_at, "
                "duration_ms, voiced, saved_for_eval, overall, intonation, rhythm, sound, "
                "result_json) VALUES (?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?)",
                (
                    lesson_id,
                    segment_index,
                    attempt,
                    _now_iso(),
                    duration_ms,
                    scores.overall,
                    scores.intonation,
                    scores.rhythm,
                    scores.sound,
                    result.model_dump_json(by_alias=True, exclude_unset=True),
                ),
            )
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return result


def mark_saved_for_eval(lesson_id: str, segment_index: int, attempt: int) -> bool:
    """Đặt `saved_for_eval = 1`; False khi không có lượt đó (không tạo lượt mới, mục D)."""
    _check_lesson_id(lesson_id)
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE attempts SET saved_for_eval = 1 "
            "WHERE lesson_id = ? AND segment_index = ? AND attempt = ?",
            (lesson_id, segment_index, attempt),
        )
        return cursor.rowcount > 0


def get_attempt(lesson_id: str, segment_index: int, attempt: int) -> AttemptRow | None:
    _check_lesson_id(lesson_id)
    with connection() as conn:
        row = conn.execute(
            "SELECT lesson_id, segment_index, attempt, created_at, duration_ms, voiced, "
            "saved_for_eval FROM attempts "
            "WHERE lesson_id = ? AND segment_index = ? AND attempt = ?",
            (lesson_id, segment_index, attempt),
        ).fetchone()
    if row is None:
        return None
    return AttemptRow(
        lesson_id=row["lesson_id"],
        segment_index=row["segment_index"],
        attempt=row["attempt"],
        created_at=row["created_at"],
        duration_ms=row["duration_ms"],
        voiced=bool(row["voiced"]),
        saved_for_eval=bool(row["saved_for_eval"]),
    )


def segment_progress(lesson_id: str) -> list[SegmentProgressRow]:
    """Chỉ các câu đã có >= 1 lượt: số lượt (mọi upload) và số lượt voiced, theo segment_index."""
    _check_lesson_id(lesson_id)
    with connection() as conn:
        rows = conn.execute(
            "SELECT segment_index, COUNT(*) AS attempts, SUM(voiced) AS voiced_attempts "
            "FROM attempts WHERE lesson_id = ? GROUP BY segment_index ORDER BY segment_index",
            (lesson_id,),
        ).fetchall()
    return [
        SegmentProgressRow(
            segment_index=row["segment_index"],
            attempts=row["attempts"],
            voiced_attempts=row["voiced_attempts"],
        )
        for row in rows
    ]

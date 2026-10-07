"""Đọc/ghi `lesson.json` cho mọi nơi ngoài pipeline: nguồn sự thật của trạng thái bài (D-02).

Ghi luôn atomic (`write_contract_json`) và mọi read-modify-write đi qua `update_lesson`, giữ khoá
riêng của từng bài, để hai thread (job nền + request) không ghi đè nhau (T-02-09).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Iterator

from pydantic import ValidationError

from audio_service.config import data_root, lesson_json_path
from audio_service.contract_io import write_contract_json
from audio_service.contracts_gen import Lesson

logger = logging.getLogger(__name__)

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def lesson_lock(lesson_id: str) -> threading.Lock:
    """Một khoá cho mỗi bài (không phải reentrant: đừng gọi `update_lesson` lồng nhau)."""
    with _LOCKS_GUARD:
        lock = _LOCKS.get(lesson_id)
        if lock is None:
            lock = _LOCKS[lesson_id] = threading.Lock()
        return lock


def load_lesson(lesson_id: str) -> Lesson:
    """Đọc và validate `lesson.json`. Raise InvalidIdError / FileNotFoundError / ValidationError."""
    path = lesson_json_path(lesson_id)
    return Lesson.model_validate_json(path.read_text(encoding="utf-8"))


def save_lesson(lesson: Lesson) -> None:
    write_contract_json(lesson_json_path(lesson.id), lesson)


def update_lesson(lesson_id: str, fn: Callable[[Lesson], Lesson]) -> Lesson:
    """Khoá bài -> đọc -> `fn` trả bài mới -> ghi atomic -> trả bài mới."""
    with lesson_lock(lesson_id):
        updated = fn(load_lesson(lesson_id))
        save_lesson(updated)
        return updated


def iter_lessons() -> Iterator[Lesson]:
    """Mọi bài hợp lệ trong `DATA_DIR/lessons/*/lesson.json`; file hỏng bị bỏ qua, không raise."""
    root = data_root() / "lessons"
    if not root.is_dir():
        return
    for path in sorted(root.glob("*/lesson.json")):
        try:
            yield Lesson.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValidationError):
            logger.warning("bỏ qua lesson.json không đọc được: %s", path.parent.name)

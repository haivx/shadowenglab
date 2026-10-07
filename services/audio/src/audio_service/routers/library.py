"""Router library: thư viện bài học (danh sách, tiến độ).

Danh sách quét `DATA_DIR/lessons/*/lesson.json` (không có chỉ mục bài trong SQLite, D-02) rồi ghép
số câu đã tập từ bảng `attempts` (D-08: câu đã tập = có >= 1 lượt voiced). Không prefix: mỗi
endpoint tự khai báo đường dẫn đầy đủ.
"""

from __future__ import annotations

from fastapi import APIRouter

from audio_service import db
from audio_service.config import InvalidIdError, lesson_json_path
from audio_service.contract_io import dump_contract
from audio_service.contracts_gen import Lesson, LessonListItem, LessonProgress, LessonSummary
from audio_service.errors import ApiErrorException
from audio_service.lesson import store

router = APIRouter(tags=["library"])


def _summary(lesson: Lesson) -> LessonSummary:
    """LessonSummary = bài bỏ `segments`; field tuỳ chọn vắng mặt vẫn vắng mặt."""
    payload = dump_contract(lesson)
    payload.pop("segments", None)
    return LessonSummary.model_validate(payload)


@router.get("/lessons", response_model=list[LessonListItem], response_model_exclude_unset=True)
def list_lessons() -> list[LessonListItem]:
    lessons = sorted(store.iter_lessons(), key=lambda lesson: (lesson.created_at, lesson.id))
    lessons.reverse()  # mới nhất trước
    practiced = db.practiced_indexes([lesson.id for lesson in lessons])
    items: list[LessonListItem] = []
    for lesson in lessons:
        count = len(lesson.segments)
        done = {index for index in practiced[lesson.id] if index < count}
        items.append(
            LessonListItem.model_validate(
                {
                    "lesson": _summary(lesson),
                    "segmentCount": count,
                    "practicedCount": len(done),
                    "firstUnpracticedIndex": db.first_unpracticed_index(count, done),
                }
            )
        )
    return items


@router.get(
    "/lessons/{lesson_id}/progress",
    response_model=LessonProgress,
    response_model_exclude_unset=True,
)
def lesson_progress(lesson_id: str) -> LessonProgress:
    try:
        lesson_json_path(lesson_id)  # chỉ để kiểm id (ULID_RE + nằm trong DATA_DIR)
        lesson = store.load_lesson(lesson_id)
    except (InvalidIdError, OSError, ValueError):
        # ValidationError là ValueError: file hỏng đối xử như không có bài.
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài.") from None
    rows = db.segment_progress(lesson_id)
    practiced = {row.segment_index for row in rows if row.voiced_attempts >= 1}
    return LessonProgress.model_validate(
        {
            "lessonId": lesson_id,
            "segments": [
                {
                    "segmentIndex": row.segment_index,
                    "attempts": row.attempts,
                    "voicedAttempts": row.voiced_attempts,
                }
                for row in rows
            ],
            "firstUnpracticedIndex": db.first_unpracticed_index(len(lesson.segments), practiced),
        }
    )

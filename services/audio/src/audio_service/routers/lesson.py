from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from audio_service.config import InvalidIdError, lesson_json_path
from audio_service.contracts_gen import Lesson

router = APIRouter(prefix="/lessons", tags=["lesson"])


@router.get("/{lesson_id}", response_model=Lesson, response_model_exclude_unset=True)
def get_lesson(lesson_id: str) -> Lesson:
    try:
        path = lesson_json_path(lesson_id)
    except InvalidIdError:
        raise HTTPException(status_code=404, detail="lesson not found") from None
    if not path.is_file():
        raise HTTPException(status_code=404, detail="lesson not found")
    try:
        return Lesson.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, UnicodeDecodeError):
        # Không đưa đường dẫn hay chi tiết lỗi ra ngoài.
        raise HTTPException(status_code=500, detail="stored lesson is invalid") from None

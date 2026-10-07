"""Router media: video của bài (S3), xem trước link (S2), tải lại video.

`GET /lessons/{id}/video` phát file tự host `DATA_DIR/videos/{videoId}/video.mp4` (D-17, ADR 0004).
videoId chỉ đọc từ `lesson.json`, client không bao giờ gửi videoId hay đường dẫn (T-02-17).
Range / 206 / 416 / Accept-Ranges do Starlette `FileResponse` lo, không tự viết.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import ValidationError

from audio_service.config import InvalidIdError, video_asset_path
from audio_service.errors import ApiErrorException
from audio_service.lesson import store

router = APIRouter(tags=["media"])


@router.get("/lessons/{lesson_id}/video")
def get_lesson_video(lesson_id: str) -> FileResponse:
    try:
        lesson = store.load_lesson(lesson_id)
    except (InvalidIdError, FileNotFoundError, ValidationError, UnicodeDecodeError):
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài.") from None
    if lesson.status != "ready":
        raise ApiErrorException(404, "not_found", "Bài chưa sẵn sàng.")

    try:
        path = video_asset_path(lesson.video_id, "video.mp4")
    except InvalidIdError:
        raise ApiErrorException(
            404, "not_found", "Không tìm thấy file video của bài này."
        ) from None
    if not path.is_file():
        raise ApiErrorException(404, "not_found", "Không tìm thấy file video của bài này.")
    return FileResponse(path, media_type="video/mp4")

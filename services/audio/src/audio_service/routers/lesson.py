"""Tạo bài, đọc bài (S1/S3 poll), thử lại bài lỗi. Pipeline không chạy trong request (D-01):
request chỉ ghi bài `queued` rồi giao cho `JobRunner`."""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from audio_service.config import InvalidIdError, lesson_json_path
from audio_service.contracts_gen import CreateLessonRequest, Lesson
from audio_service.errors import ApiErrorException
from audio_service.lesson import pipeline, store
from audio_service.lesson.jobs import InvalidState, JobRunner, retry_lesson
from audio_service.lesson.urls import InvalidYoutubeUrl, parse_youtube_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lessons", tags=["lesson"])

# Kiểm tra trùng + ghi bài phải liền nhau, nếu không hai POST cùng lúc cùng qua được kiểm tra.
_create_lock = threading.Lock()


def _runner(request: Request) -> JobRunner:
    runner: JobRunner = request.app.state.runner
    return runner


@router.post("", status_code=201, response_model=Lesson, response_model_exclude_unset=True)
def create_lesson(body: CreateLessonRequest, request: Request) -> Lesson:
    deps: pipeline.PipelineDeps = request.app.state.deps
    try:
        video_id = parse_youtube_url(body.url)
    except InvalidYoutubeUrl:
        raise ApiErrorException(
            400, "invalid_url", "Link này không phải link video YouTube."
        ) from None

    # fetch_info là lời gọi mạng duy nhất trong request (cache info.json khi đã có).
    try:
        info = deps.fetch_info(video_id)
    except pipeline.DownloadError:
        raise ApiErrorException(
            404, "video_unavailable", "Không tìm thấy video hoặc video không khả dụng."
        ) from None
    except Exception:
        logger.exception("fetch_info lỗi cho video %s", video_id)
        raise ApiErrorException(
            502, "upstream_error", "Không lấy được thông tin video lúc này. Hãy thử lại."
        ) from None

    try:
        start, end = pipeline.resolve_range(
            info.duration_sec, body.start, body.end, use_default=True
        )
    except ValueError:
        raise ApiErrorException(422, "invalid_range", "Khoảng thời gian không hợp lệ.") from None

    with _create_lock:
        for existing in store.iter_lessons():
            if (
                existing.video_id == video_id
                and existing.status != "failed"
                and existing.range.start == start
                and existing.range.end == end
            ):
                raise ApiErrorException(
                    409,
                    "duplicate_lesson",
                    "Bạn đã có bài cho đoạn này của video.",
                    lesson_id=existing.id,
                )
        lesson = pipeline.create_lesson(body.url, start=start, end=end, deps=deps, info=info)
    runner = _runner(request)
    runner.submit(lesson.id)
    return lesson


@router.post(
    "/{lesson_id}/retry", status_code=202, response_model=Lesson, response_model_exclude_unset=True
)
def retry(lesson_id: str, request: Request) -> Lesson:
    try:
        return retry_lesson(lesson_id, _runner(request))
    except (InvalidIdError, FileNotFoundError):
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài này.") from None
    except InvalidState:
        raise ApiErrorException(409, "invalid_state", "Bài này không ở trạng thái lỗi.") from None


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

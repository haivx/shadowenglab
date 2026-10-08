"""Router media: video của bài (S3), xem trước link (S2), tải lại video.

`GET /videos/preview?url=` (S2) kiểm tra link bằng allow-list URL TRƯỚC khi gọi yt-dlp, và yt-dlp
chỉ nhận video id đã kiểm tra (T-02-18). Mọi lỗi trả message tiếng Việt cố định, không bao giờ
chứa chữ của yt-dlp hay đường dẫn (T-02-20).

`GET /lessons/{id}/video` phát file tự host `DATA_DIR/videos/{videoId}/video.mp4` (D-17, ADR 0004).
videoId chỉ đọc từ `lesson.json`, client không bao giờ gửi videoId hay đường dẫn (T-02-17).
Range / 206 / 416 / Accept-Ranges do Starlette `FileResponse` lo, không tự viết.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, Response
from pydantic import ValidationError
from yt_dlp.utils import DownloadError

from audio_service.config import InvalidIdError, video_asset_path
from audio_service.contracts_gen import VideoPreview
from audio_service.errors import ApiErrorException
from audio_service.lesson import download, pipeline, store
from audio_service.lesson.download import LIVE_STATUSES, VideoInfo
from audio_service.lesson.urls import (
    MAX_URL_LEN,
    InvalidYoutubeUrl,
    is_channel_url,
    parse_youtube_url,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

# Copy cố định theo UI-SPEC S2 (không đổi chữ ở đây mà không đổi UI-SPEC).
CHANNEL_URL_MESSAGE = "Đây là link kênh. Hãy dán link một video (có “watch?v=” hoặc “youtu.be/”)."
INVALID_URL_MESSAGE = (
    "Link này không phải link video YouTube. Hãy dán link có “watch?v=” hoặc “youtu.be/”."
)
VIDEO_UNAVAILABLE_MESSAGE = (
    "Không lấy được video này (giới hạn khu vực, video riêng tư hoặc livestream). Thử video khác."
)
UPSTREAM_MESSAGE = "Không lấy được thông tin video lúc này. Hãy thử lại."

# yt-dlp `availability` coi là xem được; giá trị khác (private, needs_auth, ...) là không dùng được.
_OPEN_AVAILABILITY = frozenset({None, "public", "unlisted"})


def ensure_video_usable(info: VideoInfo) -> None:
    """Từ chối livestream/sắp phát và video không xem được. Dùng chung cho preview và tạo bài."""
    if info.live_status in LIVE_STATUSES:
        raise ApiErrorException(422, "live_video", VIDEO_UNAVAILABLE_MESSAGE)
    if info.availability not in _OPEN_AVAILABILITY:
        raise ApiErrorException(404, "video_unavailable", VIDEO_UNAVAILABLE_MESSAGE)


def _existing_lesson_id(info: VideoInfo) -> str | None:
    """Bài không-lỗi cùng videoId và cùng khoảng mặc định (02-01 mục F, Open Q10)."""
    start, end = pipeline.default_range(info.duration_sec)
    for lesson in store.iter_lessons():
        if (
            lesson.video_id == info.video_id
            and lesson.status != "failed"
            and lesson.range.start == start
            and lesson.range.end == end
        ):
            return lesson.id
    return None


@router.get("/videos/preview", response_model=VideoPreview, response_model_exclude_unset=True)
def preview_video(request: Request, url: str = Query(max_length=MAX_URL_LEN)) -> VideoPreview:
    if is_channel_url(url):
        raise ApiErrorException(400, "channel_url", CHANNEL_URL_MESSAGE)
    try:
        video_id = parse_youtube_url(url)
    except InvalidYoutubeUrl:
        raise ApiErrorException(400, "invalid_url", INVALID_URL_MESSAGE) from None

    deps: pipeline.PipelineDeps = request.app.state.deps
    try:
        info = deps.fetch_info(video_id)
    except DownloadError:
        raise ApiErrorException(404, "video_unavailable", VIDEO_UNAVAILABLE_MESSAGE) from None
    except Exception:
        logger.exception("fetch_info lỗi cho video %s", video_id)
        raise ApiErrorException(502, "upstream_error", UPSTREAM_MESSAGE) from None

    ensure_video_usable(info)

    payload: dict[str, object] = {
        "videoId": info.video_id,
        "title": info.title,
        "durationSec": info.duration_sec,
    }
    if info.channel is not None:
        payload["channel"] = info.channel
    if info.thumbnail_url is not None:
        payload["thumbnailUrl"] = info.thumbnail_url
    existing = _existing_lesson_id(info)
    if existing is not None:
        payload["existingLessonId"] = existing
    return VideoPreview.model_validate(payload)


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


@router.post("/lessons/{lesson_id}/video/reload", status_code=204)
def reload_lesson_video(lesson_id: str, request: Request) -> Response:
    """Nút "Tải lại video" ở S3 (D-17): xoá video.mp4 rồi tải lại. Đồng bộ, UI hiện chờ."""
    try:
        lesson = store.load_lesson(lesson_id)
    except (InvalidIdError, FileNotFoundError, ValidationError, UnicodeDecodeError):
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài.") from None
    if lesson.status != "ready":
        raise ApiErrorException(409, "invalid_state", "Bài chưa sẵn sàng.")

    deps: pipeline.PipelineDeps = request.app.state.deps
    try:
        download.reload_video(lesson.video_id, deps.download_video)
    except DownloadError:
        raise ApiErrorException(502, "video_unavailable", VIDEO_UNAVAILABLE_MESSAGE) from None
    except Exception:
        logger.exception("tải lại video %s lỗi", lesson.video_id)
        raise ApiErrorException(502, "upstream_error", UPSTREAM_MESSAGE) from None
    return Response(status_code=204)

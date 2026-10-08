"""Router segments: sửa câu (PLY-04) và "Mất chữ cuối?" (PLY-05).

Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ, nên không phải sửa `main.py`.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ValidationError

from audio_service.config import InvalidIdError
from audio_service.contracts_gen import Segment
from audio_service.errors import ApiErrorException
from audio_service.lesson import segment_ops
from audio_service.lesson.jobs import InvalidState

router = APIRouter(tags=["segments"])

NOT_FOUND_MESSAGE = "Không tìm thấy bài này."
INVALID_SEGMENT_MESSAGE = "Không có câu này trong bài."
NOT_READY_MESSAGE = "Bài này chưa sẵn sàng."
BAD_TEXT_MESSAGE = "Câu không được để trống hoặc dài quá 500 ký tự."
CORRUPT_MESSAGE = "Không đọc được dữ liệu của bài này."


class _EditBody(BaseModel):
    """Cùng hình dạng dây với `UpdateSegmentTextRequest` ({text: string}).

    Độ dài 1-500 do server kiểm sau khi chuẩn hoá NFC + gộp khoảng trắng (đếm code point của chính
    server, 02-01 mục A9). Model sinh từ contract kiểm độ dài trên chuỗi thô, nên một câu viết
    dạng tổ hợp dài hơn 500 nhưng chỉ 499 sau NFC sẽ bị từ chối sai.
    """

    text: str


def lesson_error(exc: Exception) -> ApiErrorException:
    """Ánh xạ lỗi của store/segment_ops sang ApiError (message cố định, không lộ đường dẫn)."""
    if isinstance(exc, (InvalidIdError, FileNotFoundError)):
        return ApiErrorException(404, "not_found", NOT_FOUND_MESSAGE)
    if isinstance(exc, IndexError):
        return ApiErrorException(404, "invalid_segment", INVALID_SEGMENT_MESSAGE)
    if isinstance(exc, InvalidState):
        return ApiErrorException(409, "invalid_state", NOT_READY_MESSAGE)
    if isinstance(exc, (ValidationError, UnicodeDecodeError)):
        return ApiErrorException(500, "internal_error", CORRUPT_MESSAGE)
    raise exc


@router.patch(
    "/lessons/{lesson_id}/segments/{index}",
    response_model=Segment,
    response_model_exclude_unset=True,
)
def edit_segment(lesson_id: str, index: int, body: _EditBody) -> Segment:
    text = segment_ops.normalize_text(body.text)
    if not 1 <= len(text) <= segment_ops.TEXT_MAX_CHARS:
        raise ApiErrorException(422, "invalid_request", BAD_TEXT_MESSAGE)
    try:
        return segment_ops.edit_segment_text(lesson_id, index, text)
    except (
        InvalidIdError,
        FileNotFoundError,
        IndexError,
        InvalidState,
        ValidationError,
        UnicodeDecodeError,
    ) as exc:
        raise lesson_error(exc) from None

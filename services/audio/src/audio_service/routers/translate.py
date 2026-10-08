"""Router translate: dịch một câu sang tiếng Việt, cache trong lesson.json (PLY-04, D-16, D-23).

Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from audio_service import secrets_env
from audio_service.config import InvalidIdError
from audio_service.contracts_gen import Lesson, Segment
from audio_service.errors import ApiErrorException
from audio_service.lesson import store, translate

router = APIRouter(tags=["translate"])

NO_KEY_MESSAGE = "Cần OPENAI_API_KEY"
TRANSLATE_FAILED_MESSAGE = "Không dịch được câu này. Bấm Dịch để thử lại."


def get_translate_client() -> Iterator[httpx.Client]:
    """Client httpx gọi OpenAI; là dependency để test tiêm `MockTransport` (không SDK, D-23)."""
    with httpx.Client(timeout=translate.TIMEOUT_S) as client:
        yield client


def _ready_lesson(lesson_id: str, index: int) -> Lesson:
    try:
        lesson = store.load_lesson(lesson_id)
    except (InvalidIdError, OSError, ValueError):
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài.") from None
    if lesson.status != "ready":
        raise ApiErrorException(409, "invalid_state", "Bài chưa sẵn sàng.")
    if not 0 <= index < len(lesson.segments):
        raise ApiErrorException(404, "invalid_segment", "Không có câu này trong bài.")
    return lesson


@router.post(
    "/lessons/{lesson_id}/segments/{index}/translate",
    response_model=Segment,
    response_model_exclude_unset=True,
)
def translate_segment(
    lesson_id: str, index: int, client: Annotated[httpx.Client, Depends(get_translate_client)]
) -> Segment:
    """Bản dịch tiếng Việt của câu: lần đầu gọi OpenAI (chỉ text), các lần sau đọc cache.

    - Chưa có bản dịch và chưa có key -> 409 `no_openai_key` (SET-02); có cache thì không cần key.
    - OpenAI 4xx/5xx hoặc đầu ra sai -> 502 `upstream_error`; mất mạng/timeout -> 503
      `network_error`. Message cố định: không key, không body của OpenAI (T-02-45).
    """
    _ready_lesson(lesson_id, index)
    try:
        return translate.translate_segment(
            lesson_id, index, client=client, key=secrets_env.get_openai_key()
        )
    except translate.NoKeyError:
        raise ApiErrorException(409, "no_openai_key", NO_KEY_MESSAGE) from None
    except translate.UpstreamError:
        raise ApiErrorException(502, "upstream_error", TRANSLATE_FAILED_MESSAGE) from None
    except translate.NetworkError:
        raise ApiErrorException(503, "network_error", TRANSLATE_FAILED_MESSAGE) from None

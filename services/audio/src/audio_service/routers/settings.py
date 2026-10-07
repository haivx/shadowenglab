"""Router settings: cài đặt luyện tập và thư mục dữ liệu (SET-04).

Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ.
"""

import logging
from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends

from audio_service import secrets_env, settings_store
from audio_service.contracts_gen import AppSettings, OpenAiKeyCheckRequest, OpenAiKeyCheckResult
from audio_service.errors import ApiErrorException

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

BAD_DATA_DIR = "Thư mục không tồn tại hoặc không ghi được."


@router.get("/settings", response_model=AppSettings)
def get_app_settings() -> AppSettings:
    """Giá trị đã lưu, hoặc mặc định khi chưa có file (hay file hỏng)."""
    return settings_store.read_settings()


@router.put("/settings", response_model=AppSettings)
def put_app_settings(body: AppSettings) -> AppSettings:
    """Kiểm tra rồi lưu atomic. `dataDir` mới áp dụng sau restart, không chuyển dữ liệu (D-12)."""
    try:
        settings_store.validate_data_dir(body.data_dir)
    except settings_store.InvalidDataDirError:
        raise ApiErrorException(422, "invalid_settings", BAD_DATA_DIR) from None
    try:
        settings_store.write_settings(body)
    except OSError:
        logger.exception("không ghi được settings.json")
        raise ApiErrorException(500, "internal_error", "Không lưu được cài đặt.") from None
    return body


def get_http_client() -> Iterator[httpx.Client]:
    """Client httpx gọi OpenAI; là dependency để test tiêm `MockTransport` (không SDK, D-23)."""
    with httpx.Client() as client:
        yield client


def _result(payload: dict[str, object]) -> OpenAiKeyCheckResult:
    return OpenAiKeyCheckResult.model_validate(payload)


@router.post(
    "/settings/openai-key/check",
    response_model=OpenAiKeyCheckResult,
    response_model_exclude_unset=True,
)
def check_openai_key(
    body: OpenAiKeyCheckRequest, client: Annotated[httpx.Client, Depends(get_http_client)]
) -> OpenAiKeyCheckResult:
    """Kiểm tra key rồi (chỉ khi OpenAI chấp nhận) ghi `.env` và nạp nóng (SET-03, D-11).

    - Có `apiKey`: sai định dạng -> `valid false` ngay, KHÔNG gọi mạng, không ghi gì.
    - Không có `apiKey` (hoặc rỗng): kiểm tra key đã lưu; không có -> `reason no_key`.
    - 200 -> `valid true, saved true, maskedKey`; 401/403 -> `valid false`, không ghi;
      lỗi mạng/5xx -> `valid null, reason network`, không ghi.
    Key không bao giờ nằm trong response, log hay message lỗi (T-02-31).
    """
    typed = body.api_key
    if typed:
        if not secrets_env.KEY_RE.fullmatch(typed):
            return _result({"valid": False, "saved": False, "reason": "invalid"})
        key = typed
    else:
        saved_key = secrets_env.get_openai_key()
        if saved_key is None:
            return _result({"valid": None, "saved": False, "reason": "no_key"})
        key = saved_key

    verdict = secrets_env.check_openai_key(key, client)
    if verdict is None:
        return _result({"valid": None, "saved": False, "reason": "network"})
    if verdict is False:
        return _result({"valid": False, "saved": False, "reason": "invalid"})
    if typed:
        try:
            secrets_env.set_openai_key(key)
        except OSError:
            logger.error(
                "không ghi được OPENAI_API_KEY vào .env"
            )  # không kèm exc_info: tránh lộ key
            raise ApiErrorException(500, "internal_error", "Không lưu được key.") from None
    return _result({"valid": True, "saved": True, "maskedKey": secrets_env.mask_key(key)})

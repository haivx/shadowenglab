"""Router settings: cài đặt luyện tập và thư mục dữ liệu (SET-04).

Không prefix: mỗi endpoint tự khai báo đường dẫn đầy đủ.
"""

import logging

from fastapi import APIRouter

from audio_service import settings_store
from audio_service.contracts_gen import AppSettings
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

"""Đọc/ghi `~/.config/shadowenglab/settings.json` (SET-04, D-10, T-02-32, T-02-33).

- File nằm ngoài DATA_DIR; ghi atomic bằng `write_json_atomic`.
- Đọc khoan dung: thiếu hoặc hỏng -> mặc định (T-02-33), không bao giờ raise.
- Không bao giờ di chuyển dữ liệu khi đổi `dataDir` (D-12); thư mục mới chỉ áp dụng sau restart.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from pydantic import ValidationError

from audio_service.config import data_root, settings_file_path
from audio_service.contract_io import dump_contract, write_json_atomic
from audio_service.contracts_gen import AppSettings

logger = logging.getLogger(__name__)


class InvalidDataDirError(ValueError):
    """`dataDir` không phải thư mục tuyệt đối, đang tồn tại và ghi được."""


def default_settings() -> AppSettings:
    """Mặc định (02-01 mục A2): tốc độ 1, lặp 1, thời gian ghi x1.5, thư mục đang dùng, giọng US."""
    return AppSettings.model_validate(
        {
            "playbackRate": 1,
            "repeat": 1,
            "recordFactor": 1.5,
            "dataDir": str(data_root()),
            "accent": "US",
        }
    )


def read_settings() -> AppSettings:
    """Cài đặt đã lưu; thiếu/hỏng/sai contract -> mặc định (có log, không log nội dung file).

    `dataDir` đã lưu mà không còn là thư mục -> thay bằng thư mục đang dùng.
    """
    path = settings_file_path()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default_settings()
    except OSError:
        logger.warning("không đọc được settings.json, dùng mặc định")
        return default_settings()
    try:
        parsed = AppSettings.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        logger.warning("settings.json hỏng hoặc sai contract, dùng mặc định")
        return default_settings()
    if not Path(parsed.data_dir).is_dir():
        # Cùng quy tắc với config._saved_data_dir lúc khởi động: thư mục đã lưu không còn (ổ
        # ngoài rút ra...) thì báo thư mục đang dùng. Nếu không, UI PUT lại đúng đường dẫn cũ
        # và mọi lần lưu cài đặt luyện tập đều 422.
        logger.warning("dataDir đã lưu không còn là thư mục, báo thư mục đang dùng")
        parsed = parsed.model_copy(update={"data_dir": str(data_root())})
    return parsed


def validate_data_dir(value: str) -> Path:
    """Tuyệt đối + tồn tại + là thư mục + ghi được; nếu không thì `InvalidDataDirError`."""
    path = Path(value)
    if not path.is_absolute() or not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
        raise InvalidDataDirError("data dir must be an existing writable absolute directory")
    return path


def write_settings(settings: AppSettings) -> None:
    """Ghi atomic (tạo thư mục cấu hình nếu chưa có). Không đụng tới dữ liệu cũ."""
    write_json_atomic(settings_file_path(), dump_contract(settings))

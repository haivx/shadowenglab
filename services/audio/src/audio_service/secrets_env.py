"""OpenAI API key: đọc, che, (Task 3) kiểm tra và ghi vào `.env` ở gốc repo (D-11, SET-02/03).

Quy tắc cứng (T-02-30, T-02-31):
- Key không bao giờ được log, đưa vào message của exception, hay trả về client. Ra ngoài chỉ có
  `hasKey` và bản che `sk-…abcd`.
- App phải chạy được khi thiếu key: `get_openai_key()` trả None, không raise.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import httpx
from dotenv import dotenv_values, set_key

from audio_service.config import REPO_ROOT

ENV_PATH = REPO_ROOT / ".env"
ENV_FILE_VAR = "SHADOWENGLAB_ENV_FILE"  # chỉ để test/ghi đè; mặc định là `.env` ở gốc repo
KEY_VAR = "OPENAI_API_KEY"

# Chặn newline, `=`, khoảng trắng và ký tự lạ: không thể chèn thêm biến vào `.env` (T-02-30).
# `\Z` (không phải `$`) để newline cuối cũng bị loại.
KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{20,256}\Z")

OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
CHECK_TIMEOUT_S = 10


class InvalidKeyError(ValueError):
    """Key sai định dạng. Message cố định: không bao giờ chứa key (T-02-31)."""


def env_path() -> Path:
    """File `.env` đang dùng: biến `SHADOWENGLAB_ENV_FILE` nếu có, nếu không `ENV_PATH`."""
    override = os.environ.get(ENV_FILE_VAR)
    return Path(override).expanduser() if override else ENV_PATH


def get_openai_key() -> str | None:
    """`os.environ` trước (nạp nóng), rồi `.env`. Chuỗi rỗng coi như không có key."""
    value = os.environ.get(KEY_VAR, "").strip()
    if value:
        return value
    path = env_path()
    if not path.is_file():
        return None
    try:
        from_file = (dotenv_values(path).get(KEY_VAR) or "").strip()
    except OSError:
        return None
    return from_file or None


def mask_key(key: str) -> str:
    """`sk-proj-xxxxabcd` -> `sk-…abcd`: 3 ký tự đầu + "…" + 4 ký tự cuối.

    Chuỗi quá ngắn để che an toàn thì chỉ trả "…".
    """
    if len(key) < 12:
        return "…"
    return f"{key[:3]}…{key[-4:]}"


def set_openai_key(key: str) -> None:
    """Ghi key vào `.env` (giữ nguyên các dòng khác, mode 0600) rồi nạp nóng vào `os.environ`.

    Chỉ gọi sau khi OpenAI đã chấp nhận key (D-11). `dotenv.set_key` ghi qua file tạm + replace.
    """
    if not KEY_RE.fullmatch(key):
        raise InvalidKeyError("invalid OpenAI API key format")
    path = env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # Tạo sẵn với 0600 để file chưa từng có thời điểm nào đọc được bởi người khác.
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT, 0o600))
    set_key(path, KEY_VAR, key, quote_mode="never")
    os.chmod(path, 0o600)
    os.environ[KEY_VAR] = key


def check_openai_key(key: str, client: httpx.Client) -> bool | None:
    """Hỏi OpenAI `GET /v1/models`: 200 -> True, 401/403 -> False, còn lại/lỗi mạng -> None.

    Không log và không đưa key vào bất kỳ message nào; lỗi httpx bị nuốt thành None.
    """
    try:
        response = client.get(
            OPENAI_MODELS_URL,
            headers={"Authorization": f"Bearer {key}"},
            timeout=CHECK_TIMEOUT_S,
        )
    except httpx.HTTPError:
        return None
    if response.status_code == 200:
        return True
    if response.status_code in (401, 403):
        return False
    return None

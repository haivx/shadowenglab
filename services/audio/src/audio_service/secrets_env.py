"""OpenAI API key: đọc, che, (Task 3) kiểm tra và ghi vào `.env` ở gốc repo (D-11, SET-02/03).

Quy tắc cứng (T-02-30, T-02-31):
- Key không bao giờ được log, đưa vào message của exception, hay trả về client. Ra ngoài chỉ có
  `hasKey` và bản che `sk-…abcd`.
- App phải chạy được khi thiếu key: `get_openai_key()` trả None, không raise.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from audio_service.config import REPO_ROOT

ENV_PATH = REPO_ROOT / ".env"
ENV_FILE_VAR = "SHADOWENGLAB_ENV_FILE"  # chỉ để test/ghi đè; mặc định là `.env` ở gốc repo
KEY_VAR = "OPENAI_API_KEY"


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

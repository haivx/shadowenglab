"""Cấu hình dịch vụ và quy ước đường dẫn trên đĩa (D-08).

Mọi helper đường dẫn kiểm tra id bằng regex trước khi nối, rồi xác nhận kết quả
nằm trong DATA_DIR sau khi resolve (chặn path traversal và symlink thoát ra ngoài).
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# services/audio/src/audio_service/config.py -> parents[4] là gốc repo.
REPO_ROOT = Path(__file__).resolve().parents[4]

ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

VideoAsset = Literal["video.mp4", "audio.wav", "vocals.wav", "no_vocals.wav"]


class Settings(BaseSettings):
    """Đọc `.env` ở gốc repo (không theo CWD, vì uv chạy bên trong services/audio)."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        extra="ignore",  # OPENAI_API_KEY / AZURE_* trong .env không làm hỏng khởi động
    )

    data_dir: Path = Path("~/shadowenglab-data")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def data_root() -> Path:
    """DATA_DIR tuyệt đối, đã expand `~` (Pitfall 9)."""
    return get_settings().data_dir.expanduser().resolve()


class InvalidIdError(ValueError):
    """Id sai định dạng hoặc đường dẫn suy ra thoát khỏi DATA_DIR."""


def _check_id(value: str, pattern: re.Pattern[str], kind: str) -> str:
    if not pattern.fullmatch(value):
        raise InvalidIdError(f"invalid {kind}")
    return value


def _contained(candidate: Path) -> Path:
    root = data_root()
    if not candidate.resolve().is_relative_to(root):
        raise InvalidIdError("path escapes data dir")
    return candidate


def lesson_dir(lesson_id: str) -> Path:
    _check_id(lesson_id, ULID_RE, "lesson id")
    return _contained(data_root() / "lessons" / lesson_id)


def lesson_json_path(lesson_id: str) -> Path:
    return _contained(lesson_dir(lesson_id) / "lesson.json")


def segment_features_path(lesson_id: str, index: int) -> Path:
    if index < 0:
        raise InvalidIdError("invalid segment index")
    return _contained(lesson_dir(lesson_id) / "seg" / f"{index:04d}.npz")


def video_dir(video_id: str) -> Path:
    _check_id(video_id, VIDEO_ID_RE, "video id")
    return _contained(data_root() / "videos" / video_id)


def video_asset_path(video_id: str, asset: VideoAsset) -> Path:
    if asset not in ("video.mp4", "audio.wav", "vocals.wav", "no_vocals.wav"):
        raise InvalidIdError("invalid asset")
    return _contained(video_dir(video_id) / asset)

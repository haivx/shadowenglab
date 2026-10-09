"""Cấu hình dịch vụ và quy ước đường dẫn trên đĩa (D-08).

Mọi helper đường dẫn kiểm tra id bằng regex trước khi nối, rồi xác nhận kết quả
nằm trong DATA_DIR sau khi resolve (chặn path traversal và symlink thoát ra ngoài).
"""

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

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


CONFIG_DIR_VAR = "SHADOWENGLAB_CONFIG_DIR"  # test/ghi đè; mặc định ~/.config/shadowenglab (D-10)


def config_dir() -> Path:
    """Thư mục cấu hình người dùng, nằm NGOÀI DATA_DIR vì `dataDir` là một setting (D-10)."""
    override = os.environ.get(CONFIG_DIR_VAR)
    return Path(override if override else "~/.config/shadowenglab").expanduser()


def settings_file_path() -> Path:
    return config_dir() / "settings.json"


def _saved_data_dir() -> Path | None:
    """`dataDir` đã lưu trong settings.json nếu dùng được; mọi lỗi -> None (đọc khoan dung).

    Dùng được = chuỗi tuyệt đối trỏ tới thư mục đang tồn tại. Đây là đường đọc lúc khởi động nên
    không bao giờ raise: file hỏng hay đường dẫn cũ không làm app hỏng.
    """
    try:
        raw = json.loads(settings_file_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = raw.get("dataDir") if isinstance(raw, dict) else None
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    if not path.is_dir():
        logger.warning("dataDir đã lưu không còn là thư mục, dùng DATA_DIR/mặc định")
        return None
    return path


@lru_cache
def get_settings() -> Settings:
    """Phân giải một lần mỗi process (D-12: đổi dataDir áp dụng sau restart).

    Thứ tự ưu tiên `dataDir` (02-01 mục G): settings.json (nếu có khoá hợp lệ) > `DATA_DIR`
    (env/.env) > `~/shadowenglab-data`.
    """
    settings = Settings()
    saved = _saved_data_dir()
    if saved is not None:
        settings = settings.model_copy(update={"data_dir": saved})
    return settings


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


def app_db_path() -> Path:
    """File SQLite `DATA_DIR/app.db` (D-02): chỉ chứa bảng `attempts`."""
    return _contained(data_root() / "app.db")


def eval_clips_dir() -> Path:
    """`DATA_DIR/eval_clips` (02-01 mục D), tạo khi cần."""
    path = _contained(data_root() / "eval_clips")
    path.mkdir(parents=True, exist_ok=True)
    return path


def tmp_dir() -> Path:
    """`DATA_DIR/tmp` cho file tạm (normalize audio ghi âm...), tạo khi cần."""
    path = _contained(data_root() / "tmp")
    path.mkdir(parents=True, exist_ok=True)
    return path


def lesson_dir(lesson_id: str) -> Path:
    _check_id(lesson_id, ULID_RE, "lesson id")
    return _contained(data_root() / "lessons" / lesson_id)


def lesson_json_path(lesson_id: str) -> Path:
    return _contained(lesson_dir(lesson_id) / "lesson.json")


def segment_features_path(lesson_id: str, index: int) -> Path:
    if index < 0:
        raise InvalidIdError("invalid segment index")
    return _contained(lesson_dir(lesson_id) / "seg" / f"{index:04d}.npz")


def ref_prosody_path(lesson_id: str, index: int) -> Path:
    """Sidecar feature ngữ điệu của bản gốc: `seg/NNNN.prosody.npz` (03-01 mục F)."""
    if index < 0:
        raise InvalidIdError("invalid segment index")
    return _contained(lesson_dir(lesson_id) / "seg" / f"{index:04d}.prosody.npz")


def video_dir(video_id: str) -> Path:
    _check_id(video_id, VIDEO_ID_RE, "video id")
    return _contained(data_root() / "videos" / video_id)


def video_asset_path(video_id: str, asset: VideoAsset) -> Path:
    if asset not in ("video.mp4", "audio.wav", "vocals.wav", "no_vocals.wav"):
        raise InvalidIdError("invalid asset")
    return _contained(video_dir(video_id) / asset)


def stems_dir(video_id: str, start_ms: int, end_ms: int) -> Path:
    """Stem tách theo khoảng: `videos/{id}/stems/{start_ms}-{end_ms}` (D-19)."""
    if start_ms < 0 or end_ms <= start_ms:
        raise InvalidIdError("invalid stems range")
    return _contained(video_dir(video_id) / "stems" / f"{start_ms}-{end_ms}")

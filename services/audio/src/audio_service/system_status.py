"""Trạng thái hệ thống cho banner S1 và màn S8 (SET-01, D-13 đã sửa bởi D-18).

- Model thiếu = không thấy snapshot trong cache HF. Chỉ tìm trong cache (`download=False`): app
  không bao giờ tự tải (D-13, giữ D-25 Phase 1).
- Model có trong cache bắt đầu ở `loading` tới khi warm-up xong thì `ready`.
- Warm-up (D-18) = nạp -> 1 suy luận mẫu -> giải phóng, TUẦN TỰ từng model dưới `model_gate` của job
  runner; không model nào nằm lại trong RAM (đo 2.5 / 4.6 / 6.0 GB, không vừa máy 8 GB).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping
from typing import Literal

from audio_service.config import data_root
from audio_service.contracts_gen import SystemStatus
from audio_service.models import PPG_ALLOW_PATTERNS, PPG_REPO, WHISPER_REPO
from audio_service.secrets_env import get_openai_key, mask_key
from audio_service.setup_models import ensure_demucs, ensure_hf_snapshot

logger = logging.getLogger(__name__)

ModelState = Literal["missing", "loading", "ready"]
MODEL_ORDER: tuple[str, ...] = ("demucs", "whisper", "wav2vec2")

CacheCheck = Callable[[], Mapping[str, bool]]
Loader = Callable[[], None]


def real_cache_check() -> dict[str, bool]:
    """Ba model có trong cache HF không? Không gọi mạng (`local_files_only`)."""
    return {
        "demucs": ensure_demucs(download=False).ok,
        "whisper": ensure_hf_snapshot(WHISPER_REPO, None, download=False).ok,
        "wav2vec2": ensure_hf_snapshot(PPG_REPO, PPG_ALLOW_PATTERNS, download=False).ok,
    }


def model_cache_states(check: CacheCheck | None = None) -> dict[str, ModelState]:
    """Trạng thái ban đầu: có trong cache -> `loading`, không -> `missing`."""
    cached = (check or real_cache_check)()
    return {name: ("loading" if cached.get(name, False) else "missing") for name in MODEL_ORDER}


class WarmUp:
    """Trạng thái từng model, an toàn giữa thread warm-up và request handler."""

    def __init__(self, initial: Mapping[str, ModelState]) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, ModelState] = {name: initial[name] for name in MODEL_ORDER}

    def states(self) -> dict[str, ModelState]:
        with self._lock:
            return dict(self._states)

    def get(self, name: str) -> ModelState:
        with self._lock:
            return self._states[name]

    def set(self, name: str, state: ModelState) -> None:
        with self._lock:
            self._states[name] = state


_singleton_lock = threading.Lock()
_singleton: WarmUp | None = None


def get_warm_up() -> WarmUp:
    """Holder dùng chung của process; kiểm tra cache đúng một lần, khi cần lần đầu."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = WarmUp(model_cache_states())
        return _singleton


def reset_warm_up(replacement: WarmUp | None = None) -> None:
    """Đặt/xoá holder dùng chung (test)."""
    global _singleton
    with _singleton_lock:
        _singleton = replacement


def build_status(warm_up: WarmUp | None = None) -> SystemStatus:
    """`SystemStatus` đã validate bằng model sinh từ contract; `maskedKey` chỉ có khi có key."""
    states = (warm_up or get_warm_up()).states()
    key = get_openai_key()
    payload: dict[str, object] = {
        "models": states,
        "hasKey": key is not None,
        "activeDataDir": str(data_root()),
    }
    if key is not None:
        payload["maskedKey"] = mask_key(key)
    return SystemStatus.model_validate(payload)

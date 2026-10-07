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

import numpy as np

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


# --- warm-up -------------------------------------------------------------------------------------

DEMUCS_SAMPLE_RATE = 44100
ASR_SAMPLE_RATE = 16000


def _warm_demucs() -> None:
    """Nạp Demucs, tách 1 s im lặng, rồi nhả. MPS lỗi thì thử lại một lần trên CPU."""
    from audio_service.lesson import separate

    silence = np.zeros((2, DEMUCS_SAMPLE_RATE), dtype=np.float32)
    device = separate.pick_device()
    separator = separate.load_separator(device)
    try:
        try:
            separate.separate_vocals(silence, DEMUCS_SAMPLE_RATE, separator)
        except RuntimeError:
            if device != "mps":
                raise
            logger.warning("warm-up Demucs trên MPS lỗi, thử lại trên CPU", exc_info=True)
            del separator
            separate.free_accelerator_memory()
            separator = separate.load_separator("cpu")
            separate.separate_vocals(silence, DEMUCS_SAMPLE_RATE, separator)
    finally:
        del separator
        separate.free_accelerator_memory()


def _warm_whisper() -> None:
    """Whisper chạy trên 1 s im lặng rồi nhả `ModelHolder` (D-18, Pitfall 2)."""
    import mlx_whisper

    from audio_service.lesson import separate, transcribe

    try:
        mlx_whisper.transcribe(
            np.zeros(ASR_SAMPLE_RATE, dtype=np.float32),
            path_or_hf_repo=WHISPER_REPO,
            language="en",
        )
    finally:
        transcribe.release_whisper()
        separate.free_accelerator_memory()


def _warm_wav2vec2() -> None:
    """Nạp wav2vec2, tính PPG cho 1 s im lặng, rồi nhả."""
    from audio_service.lesson import features, separate

    ppg = features.load_ppg_model(separate.pick_device())
    try:
        features.compute_ppg(np.zeros(ASR_SAMPLE_RATE, dtype=np.float32), ppg)
    finally:
        del ppg
        separate.free_accelerator_memory()


def real_loaders() -> dict[str, Loader]:
    """Mỗi loader = nạp -> 1 suy luận -> giải phóng; import nặng chỉ xảy ra khi loader chạy."""
    return {"demucs": _warm_demucs, "whisper": _warm_whisper, "wav2vec2": _warm_wav2vec2}


def start_warm_up(
    gate: threading.Lock,
    loaders: Mapping[str, Loader] | None = None,
    *,
    warm_up: WarmUp | None = None,
) -> threading.Thread:
    """Chạy warm-up ở thread daemon: từng model có trong cache, theo thứ tự, mỗi cái trong `gate`.

    Giữ `model_gate` nên một job tạo bài chờ warm-up và ngược lại (không bao giờ hai model cùng
    nằm trong RAM, T-02-34). Loader lỗi -> model đó `missing` + log, các model sau vẫn chạy.
    """
    state = warm_up or get_warm_up()
    run = loaders if loaders is not None else real_loaders()

    def work() -> None:
        for name in MODEL_ORDER:
            if state.get(name) != "loading":
                continue  # thiếu trong cache: không nạp, không tải (D-13)
            loader = run.get(name)
            if loader is None:
                continue
            try:
                with gate:
                    loader()
            except Exception:
                logger.exception("warm-up %s lỗi, đánh dấu missing", name)
                state.set(name, "missing")
            else:
                state.set(name, "ready")

    thread = threading.Thread(target=work, name="model-warm-up", daemon=True)
    thread.start()
    return thread

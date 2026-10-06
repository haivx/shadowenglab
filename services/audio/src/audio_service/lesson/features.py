"""Feature của bản gốc cho từng segment: F0, năng lượng, PPG (D-24). Tính sẵn lúc tạo bài (D-08).

Các hàm nhận mảng 16 kHz mono và trả mảng, không đọc file. PPG dùng đúng
`Wav2Vec2FeatureExtractor` + `Wav2Vec2ForCTC` (Pitfall 11): không Wav2Vec2Processor, không
phonemizer, không remote code. Prominence của từ KHÔNG tính ở P0 (01-01 mục 5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_service.models import PPG_REPO

logger = logging.getLogger(__name__)

SR = 16000


def extract_f0(audio16k: np.ndarray, sr: int = SR) -> np.ndarray:
    """F0 bằng Praat autocorrelation, bước 10 ms. Hz, 0.0 = vô thanh. float32."""
    import parselmouth

    sound = parselmouth.Sound(np.asarray(audio16k, dtype=np.float64), sampling_frequency=sr)
    pitch = sound.to_pitch_ac(time_step=0.01, pitch_floor=75.0, pitch_ceiling=500.0)
    return np.asarray(pitch.selected_array["frequency"], dtype=np.float32)


def frame_energy(
    audio16k: np.ndarray, sr: int = SR, hop_s: float = 0.01, win_s: float = 0.025
) -> np.ndarray:
    """RMS theo khung: một khung mỗi `hop_s`, cửa sổ `win_s` đặt giữa khung. float32.

    Số khung = ceil(n / hop), nên 1 s ở bước 10 ms cho đúng 100 khung.
    """
    x = np.asarray(audio16k, dtype=np.float32)
    hop = max(int(round(hop_s * sr)), 1)
    win = max(int(round(win_s * sr)), 1)
    n_frames = -(-x.shape[0] // hop)
    if n_frames == 0:
        return np.zeros(0, dtype=np.float32)
    pad = win // 2
    padded = np.pad(x, (pad, pad + win))
    windows = np.lib.stride_tricks.sliding_window_view(padded, win)[::hop][:n_frames]
    return np.sqrt(np.mean(np.square(windows), axis=1)).astype(np.float32)


@dataclass
class PpgModel:
    extractor: Any
    model: Any
    device: str


def load_ppg_model(device: str) -> PpgModel:
    """Tải wav2vec2 từ HF cache (id ở models.py, T-01-18), đưa lên thiết bị, `.eval()`."""
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

    extractor = Wav2Vec2FeatureExtractor.from_pretrained(PPG_REPO)
    model = Wav2Vec2ForCTC.from_pretrained(PPG_REPO).to(device).eval()
    return PpgModel(extractor=extractor, model=model, device=device)


def _forward(audio16k: np.ndarray, ppg: PpgModel) -> np.ndarray:
    import torch

    inputs = ppg.extractor(audio16k, sampling_rate=SR, return_tensors="pt")
    with torch.inference_mode():
        logits = ppg.model(inputs.input_values.to(ppg.device)).logits
        return torch.softmax(logits, dim=-1).cpu().numpy()[0].astype(np.float32)


def compute_ppg(audio16k: np.ndarray, ppg: PpgModel) -> np.ndarray:
    """Xác suất softmax (T, C), 50 khung/s, float32.

    Nếu MPS lỗi giữa chừng: cảnh báo một lần, chuyển model sang CPU rồi thử lại một lần
    (MPS 14.8 s so với CPU 44.5 s trên 300 s audio, Pitfall 10, nên MPS là mặc định).
    """
    x = np.asarray(audio16k, dtype=np.float32)
    try:
        return _forward(x, ppg)
    except RuntimeError:
        if ppg.device != "mps":
            raise
        logger.warning("PPG trên MPS lỗi, chuyển sang CPU và thử lại một lần", exc_info=True)
        ppg.model.to("cpu")
        ppg.device = "cpu"
        return _forward(x, ppg)


def segment_window(
    start: float, end: float, pad_ms: int, end_extra_ms: int, *, lo: float, hi: float
) -> tuple[float, float]:
    """[start - pad, end + pad + endExtra] kẹp trong [lo, hi] (D-05)."""
    pad = pad_ms / 1000.0
    extra = end_extra_ms / 1000.0
    return round(max(lo, start - pad), 6), round(min(hi, end + pad + extra), 6)

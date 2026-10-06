"""Vào/ra audio của pipeline: ffmpeg (argv, không shell), đọc/ghi wav, và hai hàm mảng thuần.

Chỉ `extract_audio`, `read_audio`, `write_audio` chạm hệ thống file (CLAUDE.md: hàm xử lý audio
thuần, mảng vào, mảng ra). File ghi qua tên tạm `.part` rồi `os.replace`, nên một wav dở dang
không bao giờ trông như cache hợp lệ.
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

TARGET_SR = 16000


def extract_audio(video_path: Path, wav_path: Path) -> None:
    """ffmpeg: video -> wav 44.1 kHz stereo cho Demucs. argv list, `check=True` (T-01-15)."""
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    part = wav_path.with_name(wav_path.name + ".part")
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-c:a",
        "pcm_s16le",
        "-f",
        "wav",
        str(part),
    ]
    try:
        subprocess.run(cmd, check=True)
        os.replace(part, wav_path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    """Đọc wav thành float32, shape (channels, n)."""
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    return np.ascontiguousarray(data.T), int(sr)


def write_audio(path: Path, audio: np.ndarray, sr: int) -> None:
    """Ghi wav float32 từ mảng (channels, n), atomic."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        sf.write(part, np.asarray(audio, dtype=np.float32).T, sr, subtype="FLOAT", format="WAV")
        os.replace(part, path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def to_mono_16k(audio: np.ndarray, sr: int) -> np.ndarray:
    """Trung bình kênh rồi resample về 16 kHz (resample_poly, tỉ lệ rút gọn). float32, 1-D."""
    mono = audio if audio.ndim == 1 else audio.mean(axis=0)
    mono = np.asarray(mono, dtype=np.float32)
    if sr == TARGET_SR:
        return mono
    g = math.gcd(TARGET_SR, sr)
    return resample_poly(mono, TARGET_SR // g, sr // g).astype(np.float32)


def slice_seconds(audio_1d: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    """Cắt [start, end) giây từ mảng 1-D; chỉ số được kẹp trong [0, len]."""
    n = audio_1d.shape[-1]
    a = min(max(int(round(start * sr)), 0), n)
    b = min(max(int(round(end * sr)), a), n)
    return audio_1d[..., a:b]

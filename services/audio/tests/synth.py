"""Câu giả giọng tổng hợp, xác định theo seed, cho test chấm ngữ điệu (không có audio thật).

Mỗi "từ" là chuỗi hài (harmonic series) có F0 trượt tuyến tính từ `f0_start` đến `f0_end`, dưới
đường bao hai formant. Hai từ khác nhau có cặp formant khác nhau nên MFCC của chúng khác nhau,
giúp DTW trên MFCC có cái để bám. Giữa các từ là khe lặng ngắn; hai đầu câu là lặng có nhiễu nền
rất nhỏ.

Dùng: `from synth import DEFAULT_WORDS, synth_sentence` (thư mục `tests/` không có `__init__.py`,
pytest đã đưa nó vào `sys.path`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SR = 16000
_MAX_HARMONIC_HZ = 5000.0  # trên mức này năng lượng nhỏ, bỏ cho nhanh
_FADE_S = 0.02  # fade vào/ra mỗi từ


@dataclass(frozen=True)
class SynthWord:
    text: str
    dur_s: float
    f0_start: float
    f0_end: float
    formants: tuple[float, float]


# 5 từ, F0 quanh 150-260 Hz, mỗi từ một cặp formant riêng, từ cuối đi xuống.
DEFAULT_WORDS: tuple[SynthWord, ...] = (
    SynthWord("alpha", 0.36, 150.0, 190.0, (700.0, 1200.0)),
    SynthWord("bravo", 0.40, 200.0, 260.0, (400.0, 2200.0)),
    SynthWord("charlie", 0.44, 230.0, 180.0, (550.0, 1700.0)),
    SynthWord("delta", 0.34, 170.0, 210.0, (300.0, 900.0)),
    SynthWord("echo", 0.46, 210.0, 140.0, (800.0, 1500.0)),
)


def _envelope(freq: np.ndarray, formants: tuple[float, float]) -> np.ndarray:
    f1, f2 = formants
    env = np.exp(-0.5 * ((freq - f1) / 130.0) ** 2) + 0.7 * np.exp(
        -0.5 * ((freq - f2) / 220.0) ** 2
    )
    return env + 0.03 * np.exp(-freq / 1500.0)


def _voiced_word(
    word: SynthWord,
    *,
    dur_scale: float,
    f0_scale: float,
    flat_f0: float | None,
    f0_offset_st: float = 0.0,
    level_db: float = 0.0,
) -> np.ndarray:
    n = max(int(round(word.dur_s * dur_scale * SR)), 8)
    if flat_f0 is not None:
        f0 = np.full(n, flat_f0, dtype=np.float64)
    else:
        f0 = np.linspace(word.f0_start, word.f0_end, n) * f0_scale
    f0 = f0 * 2.0 ** (f0_offset_st / 12.0)
    phase = 2.0 * np.pi * np.cumsum(f0) / SR
    out = np.zeros(n, dtype=np.float64)
    k_max = int(_MAX_HARMONIC_HZ / float(f0.min()))
    for k in range(1, k_max + 1):
        freq = k * f0
        amp = _envelope(freq, word.formants) * (freq < _MAX_HARMONIC_HZ)
        out += amp * np.sin(k * phase)
    fade = max(int(_FADE_S * SR), 1)
    win = np.ones(n)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    win[:fade] = ramp
    win[-fade:] = ramp[::-1]
    out *= win
    return out * 10.0 ** (level_db / 20.0)


def synth_sentence(
    words: tuple[SynthWord, ...] | list[SynthWord],
    *,
    sr: int = SR,
    seed: int = 0,
    lead_s: float = 0.5,
    tail_s: float = 0.4,
    gap_s: float = 0.04,
    noise: float = 2e-4,
    level: float = 1.0,
    f0_scale: float = 1.0,
    dur_scale: float = 1.0,
    flat_f0: float | None = None,
    extra_gap_after: dict[int, float] | None = None,
    word_f0_offset_st: dict[int, float] | None = None,
    word_level_db: dict[int, float] | None = None,
) -> tuple[np.ndarray, list[tuple[str, float, float]]]:
    """Trả (audio float32 16 kHz, [(text, start_s, end_s)]) với mốc từ tính từ đầu mảng.

    `level` nhân cả tín hiệu lẫn nhiễu (bất biến mức tín hiệu phải giữ được). `dur_scale` co
    giãn cả từ lẫn khe. `extra_gap_after[i]` chèn thêm giây lặng sau từ i. `word_f0_offset_st[i]`
    nâng F0 từ i lên (semitone) và `word_level_db[i]` đổi mức từ i (dB) so với các từ còn lại; cả
    hai mặc định None (không đổi gì). Cùng tham số + seed cho cùng mảng.
    """
    if sr != SR:
        raise ValueError("synth chỉ hỗ trợ 16 kHz")
    extra = extra_gap_after or {}
    offsets = word_f0_offset_st or {}
    levels = word_level_db or {}
    pieces: list[np.ndarray] = [np.zeros(int(round(lead_s * sr)))]
    marks: list[tuple[str, float, float]] = []
    cursor = len(pieces[0])
    for i, word in enumerate(words):
        sig = _voiced_word(
            word,
            dur_scale=dur_scale,
            f0_scale=f0_scale,
            flat_f0=flat_f0,
            f0_offset_st=offsets.get(i, 0.0),
            level_db=levels.get(i, 0.0),
        )
        marks.append((word.text, cursor / sr, (cursor + len(sig)) / sr))
        pieces.append(sig)
        cursor += len(sig)
        gap = gap_s * dur_scale + extra.get(i, 0.0) if i < len(words) - 1 else 0.0
        gap_n = int(round(gap * sr))
        if gap_n:
            pieces.append(np.zeros(gap_n))
            cursor += gap_n
    pieces.append(np.zeros(int(round(tail_s * sr))))
    audio = np.concatenate(pieces)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio / peak * 0.5  # đỉnh 0.5, rồi mới cộng nhiễu
    rng = np.random.default_rng(seed)
    audio = audio + rng.normal(0.0, noise, size=audio.shape)
    return (audio * level).astype(np.float32), marks

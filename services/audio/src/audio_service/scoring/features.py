"""Feature ngữ điệu cho cả bản gốc và người học (PRO-01, RESEARCH Pattern 1).

MỘT hàm `prepare_features` duy nhất cho hai phía: cùng cắt lặng, cùng F0 hai lượt, cùng semitone,
nội suy, làm mượt, cùng MFCC. Đây là điều kiện để "bản gốc tự so = 1.0" (RESEARCH Pitfall 1).

Hàm thuần: mảng 16 kHz mono vào, mảng ra, không đọc file. `parselmouth` import lười trong hàm.
Mọi mảng theo khung dùng chung lưới 10 ms của `lesson.features.frame_energy` (lưới đó quyết định số
khung n); F0 và MFCC của Praat được đặt lên lưới này theo khung gần nhất.

Các hằng số trong file này là tham số thuật toán (RESEARCH Pattern 1), KHÔNG phải ngưỡng chấm;
ngưỡng chấm nằm ở `thresholds.py`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

from audio_service.lesson.features import SR, frame_energy

FEAT_VERSION = "pf-1"
HOP_S = 0.01

_EPS = 1e-10
_N_MFCC = 12  # c1..c12 (bỏ c0, tương quan với năng lượng)
_MFCC_WINDOW_S = 0.025

# Cắt lặng hai đầu (RESEARCH Pattern 1, Pitfall 2)
_TRIM_FLAT_RANGE_DB = 20.0  # p95 - p10 nhỏ hơn mức này: không có đoạn lặng thật
_TRIM_FLAT_BELOW_PEAK_DB = 30.0  # ... thì ngưỡng = p95 - 30 dB
_TRIM_NOISE_MARGIN_DB = 12.0  # ... ngược lại ngưỡng = p10 + 12 dB
_TRIM_FLOOR_DB = -60.0  # nhưng không thấp hơn -60 dB
_TRIM_MARGIN_FRAMES = 5

# F0 hai lượt (Hirst & De Looze)
_F0_PASS1 = (60.0, 700.0)
_F0_PASS2_FLOOR_MIN = 50.0
_F0_PASS2_CEIL_MAX = 800.0
_F0_PASS2_MIN_VOICED = 10
_F0_MIN_AUDIO_S = 0.25  # ngắn hơn: Praat không đủ cửa sổ, coi như vô thanh

# Semitone, lọc quãng tám, nội suy, làm mượt
_ST_MIN_VOICED = 5
_ST_OCTAVE_WINDOW = 9
_ST_OCTAVE_DEV = 6.0
_INTERP_MAX_GAP = 12  # khe vô thanh <= 120 ms thì nội suy
_SMOOTH_MEDIAN = 5
_SMOOTH_MEAN = 3
_MIN_MFCC_AUDIO_S = 0.05
_MFCC_STD_FLOOR = 1e-6


@dataclass(frozen=True)
class ProsodyFeatures:
    """Feature theo khung 10 ms đã cắt lặng hai đầu.

    f0_st: semitone so với median của chính người nói, NaN = vô thanh (sau nội suy).
    voiced: frame hữu thanh TRƯỚC khi nội suy. energy_db: dB theo khung.
    mfcc: (khung, 12) c1-c12 đã z-chuẩn hoá. trim_start/trim_end: chỉ số khung trên lưới chưa cắt.
    Mọi mảng theo khung có độ dài trim_end - trim_start.
    """

    f0_st: np.ndarray
    voiced: np.ndarray
    energy_db: np.ndarray
    mfcc: np.ndarray
    trim_start: int
    trim_end: int


def energy_db(audio16k: np.ndarray) -> np.ndarray:
    """dB theo khung 10 ms (lưới của frame_energy). float64."""
    energy = frame_energy(audio16k, SR).astype(np.float64)
    return 20.0 * np.log10(np.maximum(energy, _EPS))


def _trim_threshold(db: np.ndarray) -> float:
    p95 = float(np.percentile(db, 95))
    p10 = float(np.percentile(db, 10))
    if p95 - p10 < _TRIM_FLAT_RANGE_DB:
        return p95 - _TRIM_FLAT_BELOW_PEAK_DB
    return max(p10 + _TRIM_NOISE_MARGIN_DB, _TRIM_FLOOR_DB)


def trim_bounds(db: np.ndarray) -> tuple[int, int]:
    """[start, end) khung còn lại sau cắt lặng. Không có khung nào vượt ngưỡng: giữ cả clip.

    Không dùng `vad._voiced_mask`: cửa sổ bản gốc gần như không có đoạn lặng nên p10 chính là mức
    tiếng nói (RESEARCH Pitfall 2); ở đó ngưỡng phải tính từ đỉnh.
    """
    n = int(db.size)
    if n == 0:
        return 0, 0
    above = np.flatnonzero(db > _trim_threshold(db))
    if above.size == 0:
        return 0, n
    return max(0, int(above[0]) - _TRIM_MARGIN_FRAMES), min(
        n, int(above[-1]) + 1 + _TRIM_MARGIN_FRAMES
    )


def _grid_shift(x1: float) -> int:
    """Khung Praat đầu (thời điểm x1) rơi vào khung nào của lưới 10 ms; cố định, không banker."""
    return int(np.floor(x1 / HOP_S + 0.5 + 1e-6))


def _pitch_ac(x: np.ndarray, n: int, floor: float, ceiling: float) -> np.ndarray:
    import parselmouth

    sound = parselmouth.Sound(x, sampling_frequency=SR)
    pitch = sound.to_pitch_ac(time_step=HOP_S, pitch_floor=floor, pitch_ceiling=ceiling)
    freq = np.asarray(pitch.selected_array["frequency"], dtype=np.float64)
    out = np.zeros(n, dtype=np.float64)
    idx = _grid_shift(float(pitch.xs()[0])) + np.arange(freq.size)
    keep = (idx >= 0) & (idx < n)
    out[idx[keep]] = freq[keep]
    return out


def f0_two_pass(audio16k: np.ndarray, n: int | None = None) -> np.ndarray:
    """F0 Hz theo lưới n khung, 0 = vô thanh. Lượt 1 rộng 60-700 Hz, lượt 2 theo q1/q3 người nói."""
    x = np.asarray(audio16k, dtype=np.float64)
    if n is None:
        n = int(-(-x.shape[0] // int(round(HOP_S * SR))))
    if x.shape[0] < int(_F0_MIN_AUDIO_S * SR) or n == 0:
        return np.zeros(n, dtype=np.float64)
    f0 = _pitch_ac(x, n, *_F0_PASS1)
    voiced = f0[f0 > 0]
    if voiced.size >= _F0_PASS2_MIN_VOICED:
        q1, q3 = np.percentile(voiced, [25, 75])
        f0 = _pitch_ac(
            x,
            n,
            max(_F0_PASS2_FLOOR_MIN, 0.75 * float(q1)),
            min(_F0_PASS2_CEIL_MAX, 2.0 * float(q3)),
        )
    return f0


def to_semitone(f0: np.ndarray) -> np.ndarray:
    """12*log2(f0/median) trên frame hữu thanh; NaN = vô thanh hoặc nghi lỗi quãng tám (>6 st)."""
    st = np.full(f0.shape, np.nan, dtype=np.float64)
    voiced = f0 > 0
    if int(voiced.sum()) < _ST_MIN_VOICED:
        return st
    st[voiced] = 12.0 * np.log2(f0[voiced] / np.median(f0[voiced]))
    idx = np.flatnonzero(voiced)
    size = min(_ST_OCTAVE_WINDOW, idx.size | 1)
    rolling = median_filter(st[idx], size=size, mode="nearest")
    st[idx[np.abs(st[idx] - rolling) > _ST_OCTAVE_DEV]] = np.nan
    return st


def interp_smooth(st: np.ndarray) -> np.ndarray:
    """Nội suy tuyến tính qua khe NaN <= 12 khung, rồi median 5 + trung bình 3 trên từng đoạn."""
    out = np.asarray(st, dtype=np.float64).copy()
    finite = np.flatnonzero(np.isfinite(out))
    if finite.size < 2:
        return out
    for a, b in zip(finite[:-1], finite[1:], strict=True):
        gap = int(b - a - 1)
        if 0 < gap <= _INTERP_MAX_GAP:
            out[a + 1 : b] = np.interp(np.arange(a + 1, b), [a, b], [out[a], out[b]])
    mask = np.isfinite(out)
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    for lo, hi in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True):
        run = median_filter(out[lo:hi], size=_SMOOTH_MEDIAN, mode="nearest")
        out[lo:hi] = uniform_filter1d(run, size=_SMOOTH_MEAN, mode="nearest")
    return out


def mfcc_frames(audio16k: np.ndarray, n: int | None = None) -> np.ndarray:
    """MFCC c1-c12 Praat (25 ms, bước 10 ms) trên lưới n khung, hình (n, 12), chưa z-chuẩn."""
    x = np.asarray(audio16k, dtype=np.float64)
    if n is None:
        n = int(-(-x.shape[0] // int(round(HOP_S * SR))))
    if x.shape[0] < int(_MIN_MFCC_AUDIO_S * SR) or n == 0:
        return np.zeros((n, _N_MFCC), dtype=np.float64)
    import parselmouth

    sound = parselmouth.Sound(x, sampling_frequency=SR)
    mfcc = sound.to_mfcc(
        number_of_coefficients=_N_MFCC, window_length=_MFCC_WINDOW_S, time_step=HOP_S
    )
    coef = np.nan_to_num(np.asarray(mfcc.to_array(), dtype=np.float64)).T  # (khung, 13)
    shift = _grid_shift(float(mfcc.x1))
    src = np.clip(np.arange(n) - shift, 0, coef.shape[0] - 1)
    return coef[src, 1:]


def prepare_features(audio16k: np.ndarray) -> ProsodyFeatures:
    """Audio 16 kHz mono -> ProsodyFeatures đã cắt lặng. Tín hiệu rỗng hoặc câm không ném lỗi."""
    x = np.nan_to_num(np.asarray(audio16k, dtype=np.float64))
    db = energy_db(x)
    n = int(db.size)
    if n == 0:
        return ProsodyFeatures(
            f0_st=np.zeros(0),
            voiced=np.zeros(0, dtype=bool),
            energy_db=np.zeros(0),
            mfcc=np.zeros((0, _N_MFCC)),
            trim_start=0,
            trim_end=0,
        )
    threshold = _trim_threshold(db)
    start, end = trim_bounds(db)

    st = to_semitone(f0_two_pass(x, n))
    voiced = np.isfinite(st)
    f0_st = interp_smooth(st)

    mfcc = mfcc_frames(x, n)
    active = mfcc[db > threshold] if bool((db > threshold).any()) else mfcc
    mean = active.mean(axis=0)
    std = np.maximum(active.std(axis=0), _MFCC_STD_FLOOR)
    mfcc = (mfcc - mean) / std

    return ProsodyFeatures(
        f0_st=f0_st[start:end],
        voiced=voiced[start:end],
        energy_db=db[start:end],
        mfcc=mfcc[start:end],
        trim_start=start,
        trim_end=end,
    )

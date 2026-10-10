"""VAD năng lượng cho bản ghi của người học (REC-03, 02-01 mục C).

Hàm thuần: mảng 16 kHz mono vào, giá trị ra, không đọc file. Dùng `frame_energy` (RMS mỗi 10 ms).
Một khung là có tiếng khi mức dB vượt max(sàn tuyệt đối, nền ồn + biên); nền ồn là phân vị thấp
của chính bản ghi, nên tiếng ồn đều (quạt, hiss) không bị tính là nói.

Các hằng số dưới đây là GIÁ TRỊ KHỞI ĐẦU (RESEARCH A1), cần chỉnh với micro thật của Liam trong
UAT cuối phase; không đổi chúng ngoài quy trình đó.
"""

from __future__ import annotations

import numpy as np

from audio_service.lesson.features import SR, frame_energy

HOP_MS = 10  # khớp hop mặc định của frame_energy
FLOOR_DB = -50.0  # dưới mức này không bao giờ là tiếng nói
NOISE_PERCENTILE = 10.0  # nền ồn = phân vị 10 của dB các khung
MARGIN_DB = 12.0  # khung có tiếng khi dB > nền ồn + MARGIN_DB
MIN_VOICED_MS = 150  # tổng thời lượng có tiếng tối thiểu
MIN_RUN_MS = 100  # và phải có một đoạn liên tục tối thiểu
# 03-11 (Liam duyệt): nói liền không có lặng thì p10 chính là tiếng nói và nhánh tương đối không
# nhận ra. Khung > ABS_VOICED_DB cũng tính là có tiếng, nhưng chỉ khi mức năng lượng có dao động
# (p95 - p10 >= MIN_DYNAMIC_DB), để nền ồn đều (quạt) vẫn không bị tính là nói.
ABS_VOICED_DB = -35.0
MIN_DYNAMIC_DB = 6.0
_EPS = 1e-10


def _voiced_mask(audio16k: np.ndarray) -> np.ndarray:
    energy = frame_energy(audio16k, SR)
    if energy.size == 0:
        return np.zeros(0, dtype=bool)
    db = 20.0 * np.log10(np.maximum(energy.astype(np.float64), _EPS))
    noise = float(np.percentile(db, NOISE_PERCENTILE))
    mask = db > max(FLOOR_DB, noise + MARGIN_DB)
    if float(np.percentile(db, 95)) - noise >= MIN_DYNAMIC_DB:
        mask |= db > ABS_VOICED_DB
    return mask


def _longest_run(mask: np.ndarray) -> int:
    best = run = 0
    for flag in mask:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def voiced_ms(audio16k: np.ndarray) -> int:
    """Tổng số ms có tiếng (số khung có tiếng nhân HOP_MS)."""
    return int(_voiced_mask(audio16k).sum()) * HOP_MS


def is_voiced(audio16k: np.ndarray) -> bool:
    """Có tiếng nói: tổng >= MIN_VOICED_MS và có đoạn liên tục >= MIN_RUN_MS."""
    mask = _voiced_mask(audio16k)
    total = int(mask.sum()) * HOP_MS
    return total >= MIN_VOICED_MS and _longest_run(mask) * HOP_MS >= MIN_RUN_MS

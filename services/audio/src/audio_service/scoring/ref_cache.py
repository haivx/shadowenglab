"""Sidecar `seg/NNNN.prosody.npz`: cache feature ngữ điệu của bản gốc (D-03, 03-01 mục F).

Đây là rìa I/O của gói `scoring` (phần còn lại là hàm thuần); file này KHÔNG import
`lesson.pipeline`, pipeline mới import file này. Chỉ lưu feature của bản gốc, không bao giờ lưu
bản ghi hay feature của người học (PRO-04).

File đọc bằng `allow_pickle=False` (T-03-11) và chỉ hợp lệ khi `feat_version` khớp `FEAT_VERSION`
và cửa sổ khớp cửa sổ hiện tại của `.npz` cùng câu; lệch thì coi như không có cache. Ghi atomic:
vào `<tên>.part` rồi `os.replace`.
"""

from __future__ import annotations

import logging
import os

import numpy as np

from audio_service.config import ref_prosody_path, segment_features_path
from audio_service.scoring.features import FEAT_VERSION, ProsodyFeatures

logger = logging.getLogger(__name__)

_WINDOW_TOL = 1e-6


def read_feature_window(lesson_id: str, index: int) -> tuple[float, float] | None:
    """Cửa sổ (giây tuyệt đối) ghi trong `seg/NNNN.npz`; thiếu hoặc hỏng -> None."""
    try:
        with np.load(segment_features_path(lesson_id, index), allow_pickle=False) as data:
            window = np.asarray(data["window"], dtype=np.float64)
    except Exception:  # noqa: BLE001 - mọi lỗi đọc cache đều nghĩa là "không có cửa sổ"
        return None
    if window.shape != (2,) or not bool(np.all(np.isfinite(window))):
        return None
    return float(window[0]), float(window[1])


def read_ref_prosody(
    lesson_id: str, index: int, window: tuple[float, float]
) -> ProsodyFeatures | None:
    """Feature đã cache nếu còn hợp lệ với `window`; mọi lỗi hoặc lệch phiên bản/cửa sổ -> None."""
    try:
        with np.load(ref_prosody_path(lesson_id, index), allow_pickle=False) as data:
            if str(data["feat_version"]) != FEAT_VERSION:
                return None
            stored = np.asarray(data["window"], dtype=np.float64)
            if stored.shape != (2,) or not (
                abs(stored[0] - window[0]) <= _WINDOW_TOL
                and abs(stored[1] - window[1]) <= _WINDOW_TOL
            ):
                return None
            trim = np.asarray(data["trim"], dtype=np.int64)
            feats = ProsodyFeatures(
                f0_st=np.asarray(data["f0_st"], dtype=np.float64),
                voiced=np.asarray(data["voiced"], dtype=bool),
                energy_db=np.asarray(data["energy_db"], dtype=np.float64),
                mfcc=np.asarray(data["mfcc"], dtype=np.float64),
                trim_start=int(trim[0]),
                trim_end=int(trim[1]),
            )
    except Exception:  # noqa: BLE001 - file thiếu/hỏng/bị sửa tay: tính lại thay vì lỗi
        return None
    n = feats.trim_end - feats.trim_start
    consistent = (
        feats.f0_st.shape == (n,)
        and feats.voiced.shape == (n,)
        and feats.energy_db.shape == (n,)
        and feats.mfcc.ndim == 2
        and feats.mfcc.shape[0] == n
    )
    if not consistent:
        logger.warning(
            "sidecar prosody của bài %s câu %d không nhất quán, bỏ qua", lesson_id, index
        )
        return None
    return feats


def write_ref_prosody(
    lesson_id: str, index: int, window: tuple[float, float], feats: ProsodyFeatures
) -> None:
    """Ghi sidecar atomic: handle mở trên `.part` (numpy không tự thêm đuôi), rồi `os.replace`."""
    out = ref_prosody_path(lesson_id, index)
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    try:
        with part.open("wb") as handle:
            np.savez_compressed(
                handle,
                feat_version=np.array(FEAT_VERSION),
                window=np.array([window[0], window[1]], dtype=np.float64),
                trim=np.array([feats.trim_start, feats.trim_end], dtype=np.int64),
                f0_st=feats.f0_st,
                voiced=feats.voiced,
                energy_db=feats.energy_db,
                mfcc=feats.mfcc,
            )
        os.replace(part, out)
    finally:
        part.unlink(missing_ok=True)

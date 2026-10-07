"""IPA từng từ, giải mã từ PPG của audio người nói gốc (D-14, D-20, PLY-06). Hàm thuần, không IO.

IPA ở đây là thứ wav2vec2-espeak NHẬN DẠNG được trong audio gốc, không phải phát âm "chuẩn" từ
từ điển: không có G2P, không phonemizer, không bước chữ -> âm nào trong module này
(CLAUDE.md: chấm so với audio gốc). Từ nào không có phone hoặc độ tin cậy dưới ngưỡng thì không
có IPA (precision trước recall); UI hiển thị "—" cho từ đó.

Vocab của model không có dấu trọng âm (`ˈ`, `ˌ`) và không có token ranh giới từ, nên IPA không
bao giờ mang dấu trọng âm; hàm vẫn lọc phòng khi vocab đổi.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

import numpy as np

from audio_service.models import PPG_REPO

# D-20: ngưỡng ẩn IPA do Liam chốt; không chỉnh ở đây.
BLANK_AND_SPECIAL = frozenset({0, 1, 2, 3})  # <pad>(blank) / <s> / </s> / <unk> trong vocab espeak
IPA_TOL_FRAMES = 2  # nới biên từ ±2 frame (40 ms ở 50 fps)
IPA_MIN_CONF = 0.7
PPG_FPS = 50.0

_STRESS_MARKS = "ˈˌ"

Phone = tuple[int, int, float]  # (frame, token id, xác suất tại frame phát)


def decode_phones(ppg: np.ndarray) -> list[Phone]:
    """Giải mã tham lam CTC: argmax từng frame, gộp frame lặp, bỏ blank/special.

    Phone được phát ở frame đầu của mỗi chuỗi frame cùng token; một frame blank giữa hai chuỗi
    cùng token tách chúng thành hai phone (đúng CTC).
    """
    if ppg.ndim != 2 or ppg.shape[0] == 0:
        return []
    best = ppg.argmax(axis=1)
    prob = ppg.max(axis=1)
    phones: list[Phone] = []
    prev = -1
    for frame, token in enumerate(best):
        token_id = int(token)
        if token_id != prev and token_id not in BLANK_AND_SPECIAL:
            phones.append((frame, token_id, float(prob[frame])))
        prev = token_id
    return phones


def _rank(span: tuple[float, float], frame: int) -> tuple[int, float]:
    """(0, 0) nếu frame nằm trong [a, b); ngược lại (1, khoảng cách tới biên gần nhất)."""
    a, b = span
    if frame < a:
        return 1, a - frame
    if frame >= b:
        return 1, frame - b
    return 0, 0.0


def ipa_for_segment(
    ppg: np.ndarray,
    window_start: float,
    fps: float,
    word_spans: Sequence[tuple[float, float]],
    inv_vocab: Mapping[int, str],
    *,
    tol_frames: int = IPA_TOL_FRAMES,
    min_conf: float = IPA_MIN_CONF,
) -> dict[int, str]:
    """`{word_index: ipa}` chỉ gồm từ đủ tin cậy; từ vắng mặt = ẩn.

    `word_spans` là (start, end) giây tuyệt đối của từng từ; `window_start` là giây tuyệt đối của
    frame PPG đầu tiên. Mỗi phone gán cho từ có khoảng frame (nới `tol_frames`) chứa nó, ưu tiên
    từ chứa nó thật sự, rồi từ gần nhất. Độ tin cậy của từ = trung bình xác suất tại các frame
    phát phone của nó (không phải trung bình mọi frame: CTC peaky, phần lớn frame là blank).
    """
    spans = [((s - window_start) * fps, (e - window_start) * fps) for s, e in word_spans]
    per_word: list[list[tuple[str, float]]] = [[] for _ in spans]
    for frame, token_id, prob in decode_phones(ppg):
        token = inv_vocab.get(token_id)
        if token is None:
            continue
        token = token.translate({ord(c): None for c in _STRESS_MARKS})
        if not token:
            continue
        near = [i for i, (a, b) in enumerate(spans) if a - tol_frames <= frame < b + tol_frames]
        if not near:
            continue
        best = min(near, key=lambda i: (*_rank(spans[i], frame), i))
        per_word[best].append((token, prob))
    out: dict[int, str] = {}
    for index, tokens in enumerate(per_word):
        if not tokens:
            continue
        if float(np.mean([p for _, p in tokens])) >= min_conf:
            out[index] = "".join(t for t, _ in tokens)
    return out


def load_inv_vocab() -> dict[int, str]:
    """Đọc `vocab.json` của model PPG từ HF cache (make setup đã tải, không tải thêm) và đảo."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(PPG_REPO, "vocab.json", local_files_only=True)
    with open(path, encoding="utf-8") as fh:
        vocab: dict[str, int] = json.load(fh)
    return {int(index): token for token, index in vocab.items()}

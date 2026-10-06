"""Nguồn duy nhất cho id các model đã khoá (D-22, D-23, D-24).

Không có cờ CLI hay biến môi trường nào được phép ghi đè các hằng số này. Đổi model cần
Liam duyệt (CLAUDE.md); module khác phải import từ đây, không hard-code id model.
"""

from __future__ import annotations

# D-22: ASR + word timestamps (mlx-whisper).
WHISPER_REPO = "mlx-community/whisper-large-v3-turbo"

# D-24: PPG. Chỉ tải các file cần cho Wav2Vec2ForCTC + FeatureExtractor (không phonemizer).
PPG_REPO = "facebook/wav2vec2-lv-60-espeak-cv-ft"
PPG_ALLOW_PATTERNS = (
    "config.json",
    "preprocessor_config.json",
    "vocab.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "pytorch_model.bin",
)

# D-23: tách giọng. demucs 4.1.0 lấy trọng số từ repo HF `adefossez/HTDemucs`.
DEMUCS_MODEL = "htdemucs"
DEMUCS_HF_REPO = "adefossez/HTDemucs"

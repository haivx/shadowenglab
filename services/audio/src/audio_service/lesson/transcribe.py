"""ASR có mốc thời gian từng từ bằng mlx-whisper turbo (D-22). Chạy cục bộ, không gửi audio."""

from __future__ import annotations

import numpy as np

from audio_service.lesson.segment import AsrWord
from audio_service.models import WHISPER_REPO


def transcribe_words(audio16k: np.ndarray, *, offset_s: float) -> list[AsrWord]:
    """Whisper trên mảng 16 kHz mono -> các từ với mốc là giây từ đầu video (D-01).

    `offset_s` là vị trí của mẫu đầu tiên trong video gốc. Mọi scalar numpy được ép về float
    (Pitfall 6) để dựng model contract và ghi JSON được.
    """
    import mlx_whisper

    result = mlx_whisper.transcribe(
        audio16k,
        path_or_hf_repo=WHISPER_REPO,
        word_timestamps=True,
        language="en",
        condition_on_previous_text=False,  # Pitfall 12: giảm lặp/ảo giác
    )

    words: list[AsrWord] = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            text = str(w["word"])
            if not text.strip():
                continue
            start = float(w["start"]) + offset_s
            end = max(float(w["end"]) + offset_s, start)
            words.append(
                AsrWord(
                    text=text,
                    start=start,
                    end=end,
                    probability=min(max(float(w.get("probability", 0.0)), 0.0), 1.0),
                )
            )
    return words

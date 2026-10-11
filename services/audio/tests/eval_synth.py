"""Dữ liệu tổng hợp cho test của bộ eval nội bộ (Phase 4, 04-02): bài `ready`, clip eval và case.

Không có audio thật trong repo: mọi tín hiệu từ `synth.py`. Helper dựng đúng những gì app ghi ra
đĩa (`lessons/<id>/lesson.json`, stem `vocals.wav`, `eval_clips/<stem>.wav` + sidecar 4 khoá) và
đúng dạng một dòng `cases.jsonl` (dấu nhận diện câu theo 04-01 mục A3), để `eval/analyze.py` chạy
đầu-cuối mà không cần bài thật.

Dùng: `from eval_synth import write_ready_lesson, ...` (thư mục `tests/` không có `__init__.py`,
pytest đã đưa nó vào `sys.path`).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
import soundfile as sf
from synth import DEFAULT_WORDS, SynthWord, synth_sentence

from audio_service.config import REPO_ROOT

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"
SR = 16000

# Câu thứ hai, khác hẳn DEFAULT_WORDS (formant, độ dài, cuối câu đi lên); 6 từ, chữ không trùng.
OTHER_WORDS: tuple[SynthWord, ...] = (
    SynthWord("one", 0.26, 190, 175, (350, 2500)),
    SynthWord("two", 0.34, 170, 200, (900, 1300)),
    SynthWord("three", 0.24, 205, 195, (450, 950)),
    SynthWord("four", 0.30, 180, 190, (650, 2000)),
    SynthWord("five", 0.28, 185, 215, (300, 1800)),
    SynthWord("six", 0.30, 190, 250, (500, 1100)),
)


def sentence_text(words: Sequence[SynthWord]) -> str:
    """Text của câu = chữ các từ nối bằng dấu cách."""
    return " ".join(word.text for word in words)


def write_ready_lesson(
    root: Path,
    sentences: Sequence[Sequence[SynthWord]] | None = None,
    *,
    lesson_id: str = LESSON_ID,
) -> dict[str, Any]:
    """Ghi `lesson.json` (status ready) và stem `vocals.wav` vào `root`; trả dict bài (camelCase).

    Mặc định một câu `DEFAULT_WORDS` (5 từ). Mỗi câu là một `synth_sentence` (có lặng hai đầu),
    ghép liên tiếp thành stem; mốc từ và mốc câu tính theo giây tuyệt đối của stem.
    """
    chosen = list(sentences) if sentences is not None else [DEFAULT_WORDS]
    pieces: list[np.ndarray] = []
    marked: list[list[tuple[str, float, float]]] = []
    cursor = 0.0
    for position, words in enumerate(chosen):
        audio, marks = synth_sentence(list(words), seed=position + 1)
        pieces.append(audio)
        marked.append([(text, start + cursor, end + cursor) for text, start, end in marks])
        cursor += len(audio) / SR
    stem = np.concatenate(pieces)
    total = len(stem) / SR
    segments = [
        {
            "index": i,
            "text": sentence_text(words),
            "start": marks[0][1],
            "end": marks[-1][2],
            "endExtraMs": 0,
            "words": [
                {"i": w, "text": text, "start": start, "end": end, "asrProb": 0.95}
                for w, (text, start, end) in enumerate(marks)
            ],
        }
        for i, (words, marks) in enumerate(zip(chosen, marked, strict=True))
    ]
    lesson = {
        "id": lesson_id,
        "videoId": VIDEO_ID,
        "title": "Synthetic",
        "durationSec": total,
        "range": {"start": 0.0, "end": total},
        "padMs": 150,
        "status": "ready",
        "segments": segments,
        "createdAt": "2026-10-07T08:00:00.000Z",
    }
    lesson_json = root / "lessons" / lesson_id / "lesson.json"
    lesson_json.parent.mkdir(parents=True, exist_ok=True)
    lesson_json.write_text(json.dumps(lesson), encoding="utf-8")
    stems = root / "videos" / VIDEO_ID / "stems" / f"0-{round(total * 1000)}"
    stems.mkdir(parents=True, exist_ok=True)
    sf.write(stems / "vocals.wav", stem, SR, subtype="FLOAT", format="WAV")
    return lesson


def clip_stem(lesson_id: str, index: int, attempt: int) -> str:
    """Stem clip eval đúng như `routers/attempts._store_eval_clip`."""
    return f"{lesson_id}_{index:04d}_{attempt:02d}"


def write_clip(
    root: Path,
    lesson_id: str,
    index: int,
    attempt: int,
    audio: np.ndarray,
    *,
    text: str = "synthetic",
) -> str:
    """Ghi `eval_clips/<stem>.wav` (PCM_16, 16 kHz) và sidecar đúng 4 khoá; trả stem."""
    stem = clip_stem(lesson_id, index, attempt)
    clips = root / "eval_clips"
    clips.mkdir(parents=True, exist_ok=True)
    sf.write(clips / f"{stem}.wav", audio, SR, subtype="PCM_16", format="WAV")
    sidecar = {"lessonId": lesson_id, "segmentIndex": index, "attempt": attempt, "text": text}
    (clips / f"{stem}.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return stem


def case_dict(
    lesson: dict[str, Any],
    index: int,
    *,
    case_id: str,
    kind: str,
    error_type: str | None = None,
    word_index: int | None = None,
    split: str | None = "tuning",
    clip: str | None = None,
    also_present: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Một case camelCase với dấu nhận diện câu tính như 04-01 mục A3 (optional = vắng mặt)."""
    segment = lesson["segments"][index]
    case: dict[str, Any] = {
        "caseId": case_id,
        "lessonId": lesson["id"],
        "segmentIndex": index,
        "segStartMs": round(segment["start"] * 1000),
        "segEndMs": round(segment["end"] * 1000),
        "segEndExtraMs": segment["endExtraMs"],
        "segTextHash": hashlib.sha256(segment["text"].encode("utf-8")).hexdigest()[:16],
        "kind": kind,
    }
    optional: dict[str, Any] = {
        "errorType": error_type,
        "wordIndex": word_index,
        "alsoPresent": also_present,
        "split": split,
        "clip": clip,
    }
    case.update({key: value for key, value in optional.items() if value is not None})
    return case


def write_cases(path: Path, cases: Sequence[dict[str, Any]]) -> None:
    """Ghi `cases.jsonl`: mỗi dòng một case."""
    path.write_text("".join(json.dumps(case) + "\n" for case in cases), encoding="utf-8")


def load_eval(name: str, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Nạp `eval/<name>.py` (không phải package của service) như một module test.

    Thêm thư mục `eval/` vào `sys.path` (script thật chạy bằng `python eval/<name>.py` nên thư mục
    này tự vào path) để `import evalkit` hoạt động; module được gỡ khỏi `sys.modules` khi test xong.
    """
    eval_dir = Path(REPO_ROOT) / "eval"
    monkeypatch.syspath_prepend(str(eval_dir))
    spec = importlib.util.spec_from_file_location(f"eval_{name}_for_test", eval_dir / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def listing(root: Path) -> list[tuple[str, int, int]]:
    """Mọi file và thư mục dưới `root`: (đường dẫn tương đối, kích thước, mtime ns)."""
    entries = []
    for path in sorted(root.rglob("*")):
        stat = path.stat()
        size = stat.st_size if path.is_file() else -1
        entries.append((str(path.relative_to(root)), size, stat.st_mtime_ns))
    return entries

"""Router attempts: lượt ghi âm của người học (REC-02, REC-03, REC-04).

POST nhận bản ghi của trình duyệt, chuẩn hoá thành WAV 16 kHz mono, quyết định có tiếng hay không
(VAD), ghi một dòng `attempts` rồi xoá mọi file của bản ghi. Không prefix: mỗi endpoint tự khai báo
đường dẫn đầy đủ.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, UploadFile

from audio_service import db
from audio_service.config import InvalidIdError, tmp_dir
from audio_service.contracts_gen import AttemptAck, Lesson
from audio_service.errors import ApiErrorException
from audio_service.lesson import audio_io, normalize, store, vad

router = APIRouter(tags=["attempts"])

CHUNK_BYTES = 64 * 1024
SNIFF_BYTES = 16


def _unsupported() -> ApiErrorException:
    return ApiErrorException(415, "unsupported_media", "Định dạng bản ghi không hỗ trợ.")


def _ready_lesson(lesson_id: str, index: int) -> Lesson:
    """Bài phải tồn tại, sẵn sàng và có câu `index` (không lộ đường dẫn hay chi tiết lỗi)."""
    try:
        lesson = store.load_lesson(lesson_id)
    except (InvalidIdError, OSError, ValueError):
        raise ApiErrorException(404, "not_found", "Không tìm thấy bài.") from None
    if lesson.status != "ready":
        raise ApiErrorException(409, "invalid_state", "Bài chưa sẵn sàng.")
    if not 0 <= index < len(lesson.segments):
        raise ApiErrorException(404, "invalid_segment", "Không có câu này trong bài.")
    return lesson


def _receive(upload: UploadFile, workdir: Path) -> tuple[Path, str]:
    """Ghi upload vào `workdir` theo khối 64 KB, trả (đường dẫn, demuxer đã nhận diện)."""
    src = workdir / "upload.bin"
    head = b""
    with src.open("wb") as out:
        while chunk := upload.file.read(CHUNK_BYTES):
            if len(head) < SNIFF_BYTES:
                head = (head + chunk)[:SNIFF_BYTES]
            out.write(chunk)
    demuxer = normalize.sniff_demuxer(head)
    if demuxer is None:
        raise _unsupported()
    return src, demuxer


def _normalize(upload: UploadFile, workdir: Path) -> tuple[Path, int, bool]:
    """Upload -> WAV 16 kHz mono; trả (wav, durationMs, voiced)."""
    src, demuxer = _receive(upload, workdir)
    wav = workdir / "normalized.wav"
    normalize.normalize_to_wav16k(src, wav, demuxer)
    audio, sr = audio_io.read_audio(wav)
    mono = audio_io.to_mono_16k(audio, sr)
    duration_ms = round(mono.shape[-1] * 1000 / audio_io.TARGET_SR)
    return wav, duration_ms, vad.is_voiced(mono)


@router.post(
    "/lessons/{lesson_id}/segments/{index}/attempts",
    status_code=201,
    response_model=AttemptAck,
    response_model_exclude_unset=True,
)
def create_attempt(
    lesson_id: str,
    index: int,
    audio: UploadFile,
    saveForEval: bool = Form(False),  # noqa: N803 - tên field multipart theo contract
) -> AttemptAck:
    lesson = _ready_lesson(lesson_id, index)
    workdir = Path(tempfile.mkdtemp(dir=tmp_dir()))
    try:
        _wav, duration_ms, voiced = _normalize(audio, workdir)
        attempt = db.insert_attempt(lesson.id, index, duration_ms=duration_ms, voiced=voiced)
    except subprocess.SubprocessError:
        raise _unsupported() from None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    # Tracer: `saveForEval` được nhận nhưng chưa lưu clip (Task 3 hoàn thiện); luôn false.
    return AttemptAck.model_validate(
        {
            "lessonId": lesson.id,
            "segmentIndex": index,
            "attempt": attempt,
            "durationMs": duration_ms,
            "voiced": voiced,
            "savedForEval": False,
        }
    )

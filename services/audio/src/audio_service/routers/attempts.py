"""Router attempts: lượt ghi âm của người học (REC-02, REC-03, REC-04).

POST nhận bản ghi của trình duyệt, chuẩn hoá thành WAV 16 kHz mono, quyết định có tiếng hay không
(VAD), ghi một dòng `attempts` rồi xoá mọi file của bản ghi. Không prefix: mỗi endpoint tự khai báo
đường dẫn đầy đủ.

Bản ghi là dữ liệu không tin cậy (T-02-25/26/27): kích thước chặn ở 10 MB (header và khi đọc luồng),
container chỉ nhận webm/mp4 theo magic bytes, ffmpeg chạy với `-f` tường minh, thời lượng tối đa
60 s, và thư mục tạm riêng bị xoá trong `finally` ở mọi đường thoát.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

import soundfile as sf
from fastapi import APIRouter, Form, Request, Response, UploadFile
from fastapi.routing import APIRoute
from starlette.types import Message

from audio_service import db
from audio_service.config import InvalidIdError, eval_clips_dir, tmp_dir
from audio_service.contract_io import write_json_atomic
from audio_service.contracts_gen import AttemptAck, Lesson
from audio_service.errors import ApiErrorException
from audio_service.lesson import audio_io, normalize, store, vad

CHUNK_BYTES = 64 * 1024
SNIFF_BYTES = 16
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_BODY_BYTES = MAX_UPLOAD_BYTES + CHUNK_BYTES  # chừa phần khung multipart quanh file
MAX_RECORDING_MS = 60_000


def _too_large() -> ApiErrorException:
    return ApiErrorException(413, "payload_too_large", "Bản ghi quá lớn.")


def _unsupported() -> ApiErrorException:
    return ApiErrorException(415, "unsupported_media", "Định dạng bản ghi không hỗ trợ.")


class _BoundedBodyRoute(APIRoute):
    """Chặn body > 10 MB trước khi Starlette parse multipart.

    FastAPI đọc xong form (và có thể spool ra đĩa) rồi mới chạy handler, nên giới hạn phải đặt ở
    mức route: kiểm `content-length` ngay, và đếm byte khi `receive()` để chặn cả body chunked.
    """

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        original = super().get_route_handler()

        async def handler(request: Request) -> Response:
            declared = request.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
                raise _too_large()

            received = 0
            exceeded = False
            inner = request.receive

            async def receive() -> Message:
                nonlocal received, exceeded
                message = await inner()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > MAX_BODY_BYTES:
                        exceeded = True
                        raise _too_large()
                return message

            try:
                return await original(Request(request.scope, receive))
            except Exception:
                # FastAPI bọc lỗi lúc parse body thành 400; trả đúng 413 theo contract.
                if exceeded:
                    raise _too_large() from None
                raise

        return handler


router = APIRouter(tags=["attempts"], route_class=_BoundedBodyRoute)


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
    """Ghi upload vào `workdir` theo khối 64 KB, trả (đường dẫn, demuxer đã nhận diện).

    Dừng ngay khi vượt 10 MB; magic bytes không phải webm/mp4 thì không bao giờ tới ffmpeg.
    """
    src = workdir / "upload.bin"
    head = b""
    total = 0
    with src.open("wb") as out:
        while chunk := upload.file.read(CHUNK_BYTES):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise _too_large()
            if len(head) < SNIFF_BYTES:
                head = (head + chunk)[:SNIFF_BYTES]
            out.write(chunk)
    demuxer = normalize.sniff_demuxer(head)
    if demuxer is None:
        raise _unsupported()
    return src, demuxer


def _normalize(upload: UploadFile, workdir: Path) -> tuple[Path, int, bool]:
    """Upload -> WAV 16 kHz mono; trả (wav, durationMs, voiced). ffmpeg lỗi -> 415 cố định."""
    src, demuxer = _receive(upload, workdir)
    wav = workdir / "normalized.wav"
    try:
        normalize.normalize_to_wav16k(src, wav, demuxer)
        audio, sr = audio_io.read_audio(wav)
    except (subprocess.SubprocessError, sf.LibsndfileError):
        raise _unsupported() from None
    mono = audio_io.to_mono_16k(audio, sr)
    duration_ms = round(mono.shape[-1] * 1000 / audio_io.TARGET_SR)
    if duration_ms > MAX_RECORDING_MS:
        raise ApiErrorException(422, "recording_too_long", "Bản ghi dài quá 60 giây.")
    return wav, duration_ms, vad.is_voiced(mono)


def _ack(
    lesson_id: str, index: int, attempt: int, duration_ms: int, voiced: bool, saved: bool
) -> AttemptAck:
    return AttemptAck.model_validate(
        {
            "lessonId": lesson_id,
            "segmentIndex": index,
            "attempt": attempt,
            "durationMs": duration_ms,
            "voiced": voiced,
            "savedForEval": saved,
        }
    )


def _store_eval_clip(lesson: Lesson, index: int, attempt: int, wav_path: Path) -> None:
    """Chép WAV đã chuẩn hoá vào `eval_clips/` kèm sidecar JSON (D-09, REC-04).

    Tên file chỉ dựng từ giá trị đã kiểm (ULID của bài đã load, số nguyên), không bao giờ từ tên
    file người dùng gửi (T-02-28). WAV ghi qua `.part` rồi mới đổi tên, sau sidecar, nên không có
    clip nào xuất hiện mà thiếu sidecar.
    """
    stem = f"{lesson.id}_{index:04d}_{attempt:02d}"
    clips = eval_clips_dir()
    wav = clips / f"{stem}.wav"
    part = clips / f"{stem}.wav.part"
    try:
        shutil.copyfile(wav_path, part)
        write_json_atomic(
            clips / f"{stem}.json",
            {
                "lessonId": lesson.id,
                "segmentIndex": index,
                "attempt": attempt,
                "text": lesson.segments[index].text,
            },
        )
        os.replace(part, wav)
    finally:
        part.unlink(missing_ok=True)


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
        wav, duration_ms, voiced = _normalize(audio, workdir)
        attempt = db.insert_attempt(lesson.id, index, duration_ms=duration_ms, voiced=voiced)
        if saveForEval:
            # Chỉ đánh dấu sau khi clip đã nằm trên đĩa: dòng DB không bao giờ nói dối.
            _store_eval_clip(lesson, index, attempt, wav)
            db.mark_saved_for_eval(lesson.id, index, attempt)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return _ack(lesson.id, index, attempt, duration_ms, voiced, saveForEval)


@router.put(
    "/lessons/{lesson_id}/segments/{index}/attempts/{attempt}/eval-clip",
    response_model=AttemptAck,
    response_model_exclude_unset=True,
)
def save_eval_clip(lesson_id: str, index: int, attempt: int, audio: UploadFile) -> AttemptAck:
    """Lưu clip cho eval sau khi tập: gửi lại blob trình duyệt còn giữ, không tạo lượt mới."""
    lesson = _ready_lesson(lesson_id, index)
    row = db.get_attempt(lesson.id, index, attempt)
    if row is None:
        raise ApiErrorException(404, "not_found", "Không tìm thấy lượt này.")
    workdir = Path(tempfile.mkdtemp(dir=tmp_dir()))
    try:
        wav, _duration_ms, _voiced = _normalize(audio, workdir)
        _store_eval_clip(lesson, index, attempt, wav)
        db.mark_saved_for_eval(lesson.id, index, attempt)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return _ack(lesson.id, index, attempt, row.duration_ms, row.voiced, True)

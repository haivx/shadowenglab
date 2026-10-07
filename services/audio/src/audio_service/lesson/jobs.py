"""Job runner trong process: tải song song, bước model một bài một lúc theo thứ tự nộp (D-01).

Hai giai đoạn nối nhau:
- tải (yt-dlp + ffmpeg): `ThreadPoolExecutor(download_slots)`, nhiều bài chạy song song;
- model (Demucs -> Whisper -> tách câu -> PPG): MỘT thread "model-worker", giữ `model_gate`.

Thứ tự bước model = thứ tự `submit` (kể cả khi bài nộp sau tải xong trước): hàng đợi giữ future của
bước tải theo thứ tự nộp, worker chờ từng future rồi mới chạy bước model. Một bài tải lỗi chỉ bị
bỏ qua, không chặn bài sau. Thread chỉ tạo trong `start()`, không bao giờ lúc import.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

logger = logging.getLogger(__name__)

StageFn = Callable[[str], object]
FailFn = Callable[[str, BaseException], None]


class JobRunner:
    def __init__(
        self,
        stage_download: StageFn,
        stage_model: StageFn,
        mark_failed: FailFn,
        download_slots: int = 2,
    ) -> None:
        self._stage_download = stage_download
        self._stage_model = stage_model
        self._mark_failed = mark_failed
        self._download_slots = download_slots
        self._pool: ThreadPoolExecutor | None = None
        self._worker: threading.Thread | None = None
        self._queue: queue.Queue[tuple[str, Future[bool]] | None] = queue.Queue()
        self._submit_lock = threading.Lock()
        # Dùng chung với extend-end (Pattern 1): ai cần model thì giữ cổng này.
        self.model_gate = threading.Lock()

    def start(self) -> None:
        if self._pool is not None:
            return
        self._pool = ThreadPoolExecutor(
            max_workers=self._download_slots, thread_name_prefix="lesson-download"
        )
        self._worker = threading.Thread(target=self._model_loop, name="model-worker", daemon=True)
        self._worker.start()

    def submit(self, lesson_id: str) -> None:
        pool = self._pool
        if pool is None:
            raise RuntimeError("JobRunner chưa start()")
        # Khoá để thứ tự vào hàng đợi đúng bằng thứ tự gọi submit.
        with self._submit_lock:
            future = pool.submit(self._download_job, lesson_id)
            self._queue.put((lesson_id, future))

    def stop(self) -> None:
        """Dừng nhận việc: nhả worker bằng sentinel, không chờ job đang chạy."""
        pool, self._pool = self._pool, None
        if pool is None:
            return
        self._queue.put(None)
        pool.shutdown(wait=False, cancel_futures=True)

    def _download_job(self, lesson_id: str) -> bool:
        try:
            self._stage_download(lesson_id)
        except BaseException as exc:
            self._fail(lesson_id, exc)
            return False
        return True

    def _model_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            lesson_id, future = item
            try:
                if not future.result():
                    continue  # tải lỗi: đã đánh dấu failed
            except BaseException:  # future bị huỷ khi stop()
                continue
            with self.model_gate:
                try:
                    self._stage_model(lesson_id)
                except BaseException as exc:  # worker không bao giờ chết vì một bài
                    self._fail(lesson_id, exc)

    def _fail(self, lesson_id: str, exc: BaseException) -> None:
        try:
            self._mark_failed(lesson_id, exc)
        except Exception:
            logger.exception("mark_failed lỗi cho bài %s", lesson_id)


# --- RED stubs (02-03 Task 2): thay bằng bản thật ở commit GREEN ---


class InvalidState(Exception):
    """Bài không ở trạng thái cho phép thao tác (HTTP 409 invalid_state)."""


def recover_interrupted() -> list[str]:
    raise NotImplementedError


def retry_lesson(lesson_id: str, runner: JobRunner) -> object:
    raise NotImplementedError

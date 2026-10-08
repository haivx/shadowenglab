"""Bảo đảm của hàng đợi job: không chặn, một bước model một lúc, FIFO, worker sống sót; thử lại,
đánh dấu gián đoạn khi khởi động, nhả Whisper (D-01, D-03, D-18). Không model, không mạng:
stage giả dùng `threading.Event`.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_lessons_api import URL, Fakes, wait_for_status

from audio_service.config import get_settings, lesson_dir, lesson_json_path
from audio_service.contract_io import write_contract_json
from audio_service.contracts_gen import Lesson
from audio_service.lesson import store, transcribe
from audio_service.lesson.jobs import InvalidState, JobRunner, recover_interrupted, retry_lesson
from audio_service.main import create_app

WAIT_S = 5.0


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


class Recorder:
    """Sổ ghi thứ tự/đồng thời của các stage giả."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.model_order: list[str] = []
        self.failures: list[tuple[str, BaseException]] = []
        self.inside_model = 0
        self.max_inside_model = 0
        self.model_done = threading.Semaphore(0)

    def enter_model(self, lesson_id: str) -> None:
        with self.lock:
            self.model_order.append(lesson_id)
            self.inside_model += 1
            self.max_inside_model = max(self.max_inside_model, self.inside_model)

    def leave_model(self) -> None:
        with self.lock:
            self.inside_model -= 1
        self.model_done.release()

    def mark_failed(self, lesson_id: str, exc: BaseException) -> None:
        with self.lock:
            self.failures.append((lesson_id, exc))
        self.model_done.release()  # job kết thúc (lỗi) cũng tính là xong

    def wait_done(self, n: int) -> None:
        for _ in range(n):
            assert self.model_done.acquire(timeout=WAIT_S), "job không kết thúc"


# --- bảo đảm của runner ---------------------------------------------------------------------


def test_download_of_job_b_starts_while_job_a_is_still_in_its_model_step() -> None:
    a_in_model = threading.Event()
    release_a = threading.Event()
    b_download_started = threading.Event()

    def download(lesson_id: str) -> None:
        if lesson_id == "B":
            b_download_started.set()

    def model(lesson_id: str) -> None:
        if lesson_id == "A":
            a_in_model.set()
            assert release_a.wait(WAIT_S)

    rec = Recorder()
    runner = JobRunner(download, model, rec.mark_failed)
    runner.start()
    try:
        runner.submit("A")
        assert a_in_model.wait(WAIT_S)
        runner.submit("B")
        assert b_download_started.wait(WAIT_S)  # A vẫn đang giữ bước model
        assert not release_a.is_set()
    finally:
        release_a.set()
        runner.stop()


def test_never_two_model_steps_at_once_and_model_order_is_submission_order() -> None:
    rec = Recorder()

    def download(lesson_id: str) -> None:
        if lesson_id == "1":
            time.sleep(0.15)  # bài nộp đầu tải xong SAU hai bài còn lại

    def model(lesson_id: str) -> None:
        rec.enter_model(lesson_id)
        try:
            time.sleep(0.02)
        finally:
            rec.leave_model()

    runner = JobRunner(download, model, rec.mark_failed, download_slots=2)
    runner.start()
    try:
        for lesson_id in ("1", "2", "3"):
            runner.submit(lesson_id)
        rec.wait_done(3)
    finally:
        runner.stop()

    assert rec.max_inside_model == 1
    assert rec.model_order == ["1", "2", "3"]
    assert rec.failures == []


def test_model_stage_holds_the_shared_model_gate() -> None:
    rec = Recorder()
    seen_locked: list[bool] = []
    holder: list[JobRunner] = []

    def model(_lesson_id: str) -> None:
        seen_locked.append(holder[0].model_gate.locked())
        rec.model_done.release()

    runner = JobRunner(lambda _id: None, model, rec.mark_failed)
    holder.append(runner)
    runner.start()
    try:
        runner.submit("A")
        rec.wait_done(1)
    finally:
        runner.stop()

    assert seen_locked == [True]
    assert not runner.model_gate.locked()


def test_worker_survives_a_failing_job_and_a_failing_download_does_not_reach_the_model() -> None:
    rec = Recorder()

    def download(lesson_id: str) -> None:
        if lesson_id == "DL":
            raise ConnectionError("down")

    def model(lesson_id: str) -> None:
        if lesson_id == "A":
            raise RuntimeError("boom")
        rec.enter_model(lesson_id)
        rec.leave_model()

    runner = JobRunner(download, model, rec.mark_failed)
    runner.start()
    try:
        for lesson_id in ("A", "DL", "B"):
            runner.submit(lesson_id)
        rec.wait_done(3)
    finally:
        runner.stop()

    assert {lid for lid, _ in rec.failures} == {"A", "DL"}
    assert rec.model_order == ["B"]  # B chạy dù A lỗi; DL không bao giờ vào bước model


def test_a_broken_mark_failed_does_not_kill_the_worker() -> None:
    done = threading.Event()

    def model(lesson_id: str) -> None:
        if lesson_id == "A":
            raise RuntimeError("boom")
        done.set()

    def bad_mark_failed(_lesson_id: str, _exc: BaseException) -> None:
        raise OSError("disk full")

    runner = JobRunner(lambda _id: None, model, bad_mark_failed)
    runner.start()
    try:
        runner.submit("A")
        runner.submit("B")
        assert done.wait(WAIT_S)
    finally:
        runner.stop()


# --- thử lại (LES-07, D-03) -----------------------------------------------------------------


def _failed_lesson_payload(lesson_id: str, status: str = "failed") -> dict[str, object]:
    payload: dict[str, object] = {
        "id": lesson_id,
        "videoId": "dUDi-F6eAvk",
        "title": "Demo",
        "durationSec": 12.0,
        "status": status,
        "range": {"start": 0.0, "end": 12.0},
        "padMs": 150,
        "segments": [
            {
                "index": 0,
                "text": "Hello",
                "start": 0.5,
                "end": 1.0,
                "endExtraMs": 0,
                "words": [{"i": 0, "text": "Hello", "start": 0.5, "end": 1.0, "asrProb": 0.9}],
            }
        ],
        "createdAt": "2026-10-07T08:00:00.000Z",
    }
    if status == "failed":
        payload["error"] = {"step": "analyzing", "message": "x"}
        payload["audioQuality"] = {"label": "clean", "nonVocalRatio": 0.01}
    return payload


def _write_lesson(payload: dict[str, object]) -> str:
    lesson = Lesson.model_validate(payload)
    write_contract_json(lesson_json_path(lesson.id), lesson)
    return lesson.id


ID_1 = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
ID_2 = "01HZX3Y7Q8K2M4N6P8R0S2T4V7"
ID_3 = "01HZX3Y7Q8K2M4N6P8R0S2T4V8"
ID_4 = "01HZX3Y7Q8K2M4N6P8R0S2T4V9"
ID_5 = "01HZX3Y7Q8K2M4N6P8R0S2T4VA"


class FakeRunner:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit(self, lesson_id: str) -> None:
        self.submitted.append(lesson_id)


def test_retry_of_a_failed_lesson_rebuilds_it_without_null_error_keys(data_dir: Path) -> None:
    lesson_id = _write_lesson(_failed_lesson_payload(ID_1))
    seg_file = lesson_dir(lesson_id) / "seg" / "0000.npz"
    seg_file.parent.mkdir(parents=True)
    seg_file.write_bytes(b"old features")
    runner = FakeRunner()

    returned = retry_lesson(lesson_id, runner)  # type: ignore[arg-type]

    raw = json.loads(lesson_json_path(lesson_id).read_text(encoding="utf-8"))
    assert "error" not in raw and "audioQuality" not in raw  # vắng hẳn, không phải null
    assert raw["status"] == "queued"
    assert raw["segments"] == []
    assert not (lesson_dir(lesson_id) / "seg").exists()
    assert runner.submitted == [lesson_id]
    assert returned.id == lesson_id and returned.status == "queued"
    Lesson.model_validate(raw)


def test_retry_keeps_the_identity_of_the_lesson(data_dir: Path) -> None:
    lesson_id = _write_lesson(_failed_lesson_payload(ID_1))

    retry_lesson(lesson_id, FakeRunner())  # type: ignore[arg-type]

    raw = json.loads(lesson_json_path(lesson_id).read_text(encoding="utf-8"))
    assert raw["id"] == lesson_id
    assert raw["videoId"] == "dUDi-F6eAvk"
    assert raw["range"] == {"start": 0.0, "end": 12.0}
    assert raw["createdAt"] == "2026-10-07T08:00:00.000Z"


@pytest.mark.parametrize("status", ["ready", "queued", "downloading", "analyzing"])
def test_retry_of_a_lesson_that_is_not_failed_raises_invalid_state(
    data_dir: Path, status: str
) -> None:
    lesson_id = _write_lesson(_failed_lesson_payload(ID_1, status=status))
    runner = FakeRunner()

    with pytest.raises(InvalidState):
        retry_lesson(lesson_id, runner)  # type: ignore[arg-type]

    assert runner.submitted == []
    assert json.loads(lesson_json_path(lesson_id).read_text(encoding="utf-8"))["status"] == status


def test_post_retry_on_a_ready_lesson_is_409_invalid_state(data_dir: Path) -> None:
    lesson_id = _write_lesson(_failed_lesson_payload(ID_1, status="ready"))

    with TestClient(create_app(deps=Fakes().deps()), base_url="http://127.0.0.1") as client:
        res = client.post(f"/lessons/{lesson_id}/retry")

    assert res.status_code == 409
    assert res.json()["code"] == "invalid_state"


@pytest.mark.parametrize("bad_id", ["abc", "01hzx3y7q8k2m4n6p8r0s2t4v6", ID_5])
def test_post_retry_on_an_unknown_lesson_is_404_not_found(data_dir: Path, bad_id: str) -> None:
    with TestClient(create_app(deps=Fakes().deps()), base_url="http://127.0.0.1") as client:
        res = client.post(f"/lessons/{bad_id}/retry")

    assert res.status_code == 404
    assert res.json()["code"] == "not_found"


def test_post_retry_reruns_a_failed_lesson_to_ready_with_the_same_id(data_dir: Path) -> None:
    fakes = Fakes()
    fakes.download_error = ConnectionError("offline")
    with TestClient(create_app(deps=fakes.deps()), base_url="http://127.0.0.1") as client:
        created = client.post("/lessons", json={"url": URL}).json()
        failed = wait_for_status(client, created["id"], {"failed"})
        assert failed["error"]["step"] == "downloading"

        fakes.download_error = None
        res = client.post(f"/lessons/{created['id']}/retry")
        assert res.status_code == 202
        assert res.json()["id"] == created["id"]
        final = wait_for_status(client, created["id"], {"ready", "failed"})

    assert final["status"] == "ready"
    assert "error" not in final and len(final["segments"]) == 2


def test_post_retry_is_409_duplicate_when_a_non_failed_lesson_has_the_same_video_and_range(
    data_dir: Path,
) -> None:
    fakes = Fakes()
    fakes.download_error = ConnectionError("offline")
    with TestClient(create_app(deps=fakes.deps()), base_url="http://127.0.0.1") as client:
        old = client.post("/lessons", json={"url": URL}).json()
        wait_for_status(client, old["id"], {"failed"})

        # Bài lỗi không tính là trùng nên tạo lại cùng link + khoảng được.
        fakes.download_error = None
        new = client.post("/lessons", json={"url": URL})
        assert new.status_code == 201
        wait_for_status(client, new.json()["id"], {"ready", "failed"})

        res = client.post(f"/lessons/{old['id']}/retry")
        still_failed = client.get(f"/lessons/{old['id']}").json()

    assert res.status_code == 409
    assert res.json()["code"] == "duplicate_lesson"
    assert res.json()["lessonId"] == new.json()["id"]
    assert still_failed["status"] == "failed"


# --- gián đoạn khi khởi động (D-03) ---------------------------------------------------------


def test_recover_interrupted_marks_unfinished_lessons_failed_and_leaves_the_rest(
    data_dir: Path,
) -> None:
    ids = {
        "downloading": _write_lesson(_failed_lesson_payload(ID_1, "downloading")),
        "separating": _write_lesson(_failed_lesson_payload(ID_2, "separating")),
        "queued": _write_lesson(_failed_lesson_payload(ID_3, "queued")),
        "ready": _write_lesson(_failed_lesson_payload(ID_4, "ready")),
        "failed": _write_lesson(_failed_lesson_payload(ID_5, "failed")),
    }
    before_ready = lesson_json_path(ids["ready"]).read_text(encoding="utf-8")
    before_failed = lesson_json_path(ids["failed"]).read_text(encoding="utf-8")

    changed = recover_interrupted()

    assert sorted(changed) == sorted([ids["downloading"], ids["separating"], ids["queued"]])
    for status in ("downloading", "separating", "queued"):
        lesson = store.load_lesson(ids[status])
        assert lesson.status == "failed"
        assert lesson.error is not None
        assert (lesson.error.step, lesson.error.message) == (status, "bị gián đoạn")
    assert lesson_json_path(ids["ready"]).read_text(encoding="utf-8") == before_ready
    assert lesson_json_path(ids["failed"]).read_text(encoding="utf-8") == before_failed


def test_recover_interrupted_does_not_restart_anything_and_is_idempotent(data_dir: Path) -> None:
    _write_lesson(_failed_lesson_payload(ID_1, "transcribing"))

    assert recover_interrupted() == [ID_1]
    assert recover_interrupted() == []


def test_lifespan_recovers_interrupted_lessons_before_serving(data_dir: Path) -> None:
    lesson_id = _write_lesson(_failed_lesson_payload(ID_1, "analyzing"))

    with TestClient(create_app(deps=Fakes().deps()), base_url="http://127.0.0.1") as client:
        body = client.get(f"/lessons/{lesson_id}").json()

    assert body["status"] == "failed"
    assert body["error"] == {"step": "analyzing", "message": "bị gián đoạn"}


# --- nhả Whisper (D-18, Pitfall 2) ----------------------------------------------------------


def test_release_whisper_clears_the_mlx_whisper_model_holder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ModelHolder:
        model: object | None = object()
        model_path: str | None = "mlx-community/whisper-large-v3-turbo"

    stub = types.ModuleType("mlx_whisper.transcribe")
    stub.ModelHolder = ModelHolder  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mlx_whisper.transcribe", stub)

    transcribe.release_whisper()

    assert ModelHolder.model is None
    assert ModelHolder.model_path is None


def test_release_whisper_is_a_noop_when_whisper_was_never_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "mlx_whisper.transcribe", raising=False)

    transcribe.release_whisper()  # không raise, không import mlx_whisper
    assert "mlx_whisper.transcribe" not in sys.modules


def test_default_deps_free_memory_releases_whisper(monkeypatch: pytest.MonkeyPatch) -> None:
    from audio_service.lesson import pipeline, separate

    calls: list[str] = []
    monkeypatch.setattr(transcribe, "release_whisper", lambda: calls.append("whisper"))
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: calls.append("accelerator"))

    pipeline.default_deps().free_memory()

    assert calls == ["whisper", "accelerator"]

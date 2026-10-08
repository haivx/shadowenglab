"""POST /lessons/{id}/segments/{i}/extend-end: "Mất chữ cuối?" (PLY-05, D-14, 02-01 mục E).

`endExtraMs += 300` được lưu ngay; tính lại feature + IPA chạy dưới cổng model (chờ tối đa 150 s,
test dùng 0.2 s). Không nạp model: PipelineDeps giả và một `threading.Lock` thật làm cổng.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_segment_edit import LESSON_ID, assert_no_null, make_lesson_dict, read_json, write_lesson

from audio_service.config import get_settings, segment_features_path, stems_dir
from audio_service.contracts_gen import Lesson, Segment
from audio_service.lesson import pipeline, segment_ops, store
from audio_service.lesson.audio_io import write_audio
from audio_service.lesson.pipeline import PipelineDeps
from audio_service.main import create_app

FAKE_IPA = "fɛɪk"
URL = f"/lessons/{LESSON_ID}/segments/0/extend-end"


class FakeDeps:
    """Đếm số lần nạp model và giải phóng bộ nhớ."""

    def __init__(self) -> None:
        self.load_ppg_calls = 0
        self.free_memory_calls = 0

    def deps(self) -> PipelineDeps:
        def unused(*_args: object, **_kwargs: object) -> Any:
            raise AssertionError("extend-end không được gọi stage tạo bài")

        return PipelineDeps(
            fetch_info=unused,
            download_video=unused,
            extract_audio=unused,
            separate=unused,
            transcribe=unused,
            load_ppg=self.load_ppg,
            compute_ppg=lambda clip, _m: np.full((max(len(clip) // 320, 1), 5), 0.2, np.float32),
            extract_f0=lambda clip: np.zeros(max(len(clip) // 160, 1), dtype=np.float32),
            frame_energy=lambda clip: np.zeros(max(len(clip) // 160, 1), dtype=np.float32),
            free_memory=self.free_memory,
        )

    def load_ppg(self) -> object:
        self.load_ppg_calls += 1
        return object()

    def free_memory(self) -> None:
        self.free_memory_calls += 1


class AnalyzeSpy:
    """Thay `pipeline.analyze_segment`: ghi lại câu nhận được, trả câu có IPA giả ở từ đầu."""

    def __init__(self, on_call: Callable[[Segment], None] | None = None) -> None:
        self.segments: list[Segment] = []
        self.on_call = on_call

    def __call__(self, _lesson_id: str, seg: Segment, *_args: Any, **_kwargs: Any) -> Segment:
        self.segments.append(seg)
        if self.on_call is not None:
            self.on_call(seg)
        raw = seg.model_dump(by_alias=True, exclude_unset=True)
        raw["words"][0]["ipa"] = FAKE_IPA
        return Segment.model_validate(raw)


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path.resolve()
    get_settings.cache_clear()


@pytest.fixture
def fake() -> FakeDeps:
    return FakeDeps()


@pytest.fixture
def client(data_dir: Path, fake: FakeDeps) -> Iterator[TestClient]:
    with TestClient(create_app(deps=fake.deps()), base_url="http://127.0.0.1") as test_client:
        yield test_client


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> AnalyzeSpy:
    """Stem có sẵn (mảng giả) và analyze_segment giả."""
    analyze = AnalyzeSpy()
    monkeypatch.setattr(
        pipeline, "load_range_vocals16", lambda _lesson: (np.zeros(16000 * 12, np.float32), 0.0)
    )
    monkeypatch.setattr(pipeline, "analyze_segment", analyze)
    return analyze


def test_first_call_saves_300_before_recompute_and_returns_the_updated_segment(
    client: TestClient, fake: FakeDeps, spy: AnalyzeSpy
) -> None:
    write_lesson()
    saved_when_analyzed: list[int] = []
    spy.on_call = lambda _seg: saved_when_analyzed.append(read_json()["segments"][0]["endExtraMs"])

    res = client.post(URL)

    assert res.status_code == 200
    body = res.json()
    assert body["endExtraMs"] == 300
    assert body["words"][0]["ipa"] == FAKE_IPA
    assert spy.segments[0].end_extra_ms == 300  # analyze_segment nhận câu đã nới
    assert saved_when_analyzed == [300]  # đã ghi xuống đĩa trước khi tính lại
    saved = read_json()["segments"][0]
    assert saved["endExtraMs"] == 300
    assert saved["words"][0]["ipa"] == FAKE_IPA
    assert_no_null(body)
    assert_no_null(read_json())


def test_recompute_keeps_other_segments_text_and_translation(
    client: TestClient, spy: AnalyzeSpy
) -> None:
    write_lesson()
    before = make_lesson_dict()["segments"]
    assert client.post(URL).status_code == 200
    saved = read_json()["segments"]
    assert saved[1] == before[1]
    assert saved[0]["text"] == before[0]["text"]
    assert saved[0]["translation"] == before[0]["translation"]


def test_second_call_adds_another_300(client: TestClient, spy: AnalyzeSpy) -> None:
    write_lesson(end_extra_ms=300)
    res = client.post(URL)
    assert res.json()["endExtraMs"] == 600
    assert spy.segments[0].end_extra_ms == 600


def test_busy_gate_returns_503_keeps_the_extension_and_recomputes_next_call(
    client: TestClient,
    fake: FakeDeps,
    spy: AnalyzeSpy,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_lesson()
    monkeypatch.setattr(segment_ops, "RECOMPUTE_TIMEOUT_S", 0.2)
    gate = client.app.state.runner.model_gate  # type: ignore[attr-defined]
    assert gate.acquire(timeout=1.0)
    try:
        res = client.post(URL)
    finally:
        gate.release()

    assert res.status_code == 503
    assert res.json() == {"code": "busy", "message": "Đang xử lý bài khác, thử lại sau."}
    assert read_json()["segments"][0]["endExtraMs"] == 300  # vẫn lưu
    assert "ipa" not in read_json()["segments"][0]["words"][1]
    assert spy.segments == []
    assert fake.load_ppg_calls == 0

    res = client.post(URL)  # lần sau: gate rảnh, tính lại và nới thêm 300 nữa
    assert res.status_code == 200
    assert res.json()["endExtraMs"] == 600
    assert read_json()["segments"][0]["words"][0]["ipa"] == FAKE_IPA


@pytest.mark.parametrize("start", [2700, 2800, 2900])
def test_extension_is_capped_at_3000_but_allowed_up_to_it(
    client: TestClient, spy: AnalyzeSpy, start: int
) -> None:
    write_lesson(end_extra_ms=start)
    res = client.post(URL)
    assert res.status_code == 200
    assert res.json()["endExtraMs"] == min(start + 300, 3000)


def test_at_the_cap_the_request_is_409_invalid_state_and_changes_nothing(
    client: TestClient, fake: FakeDeps, spy: AnalyzeSpy
) -> None:
    write_lesson(end_extra_ms=3000)
    res = client.post(URL)
    assert res.status_code == 409
    assert res.json() == {"code": "invalid_state", "message": "Đã nới tối đa cho câu này."}
    assert read_json()["segments"][0]["endExtraMs"] == 3000
    assert spy.segments == []
    assert fake.load_ppg_calls == 0


def test_missing_range_stems_is_409_with_the_extension_still_saved(
    client: TestClient, fake: FakeDeps, monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> None:
    write_lesson()
    analyze = AnalyzeSpy()
    monkeypatch.setattr(pipeline, "analyze_segment", analyze)  # load_range_vocals16 là bản thật

    res = client.post(URL)

    assert res.status_code == 409
    assert res.json() == {
        "code": "invalid_state",
        "message": "Bài này tạo bằng bản cũ, hãy tạo lại bài để nới câu.",
    }
    assert str(data_dir) not in res.text
    assert read_json()["segments"][0]["endExtraMs"] == 300
    assert analyze.segments == []
    assert fake.load_ppg_calls == 0


def test_model_loader_and_free_memory_run_once_per_successful_call(
    client: TestClient, fake: FakeDeps, spy: AnalyzeSpy
) -> None:
    write_lesson()
    assert client.post(URL).status_code == 200
    assert (fake.load_ppg_calls, fake.free_memory_calls) == (1, 1)
    assert client.post(URL).status_code == 200
    assert (fake.load_ppg_calls, fake.free_memory_calls) == (2, 2)


def test_memory_is_freed_and_gate_released_when_analysis_fails(
    data_dir: Path, fake: FakeDeps, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_lesson()

    def boom(*_args: object, **_kwargs: object) -> Segment:
        raise RuntimeError("secret internal detail /Users/x/path")

    monkeypatch.setattr(
        pipeline, "load_range_vocals16", lambda _l: (np.zeros(16000, np.float32), 0.0)
    )
    monkeypatch.setattr(pipeline, "analyze_segment", boom)
    with TestClient(create_app(deps=fake.deps()), base_url="http://127.0.0.1") as client:
        res = client.post(URL)
        gate = client.app.state.runner.model_gate  # type: ignore[attr-defined]
        assert gate.acquire(blocking=False)  # cổng đã được nhả
        gate.release()

    assert res.status_code == 500
    assert res.json()["code"] == "internal_error"
    assert "secret" not in res.text and "/Users" not in res.text
    assert (fake.load_ppg_calls, fake.free_memory_calls) == (1, 1)
    assert read_json()["segments"][0]["endExtraMs"] == 300


def test_a_text_edit_during_recompute_is_not_lost(client: TestClient, spy: AnalyzeSpy) -> None:
    write_lesson()
    spy.on_call = lambda _seg: segment_ops.edit_segment_text(
        LESSON_ID, 0, "Hello there our friend!"
    )

    res = client.post(URL)

    assert res.status_code == 200
    saved = read_json()["segments"][0]
    assert saved["text"] == "Hello there our friend!"
    assert "translation" not in saved
    assert saved["words"][0]["ipa"] == FAKE_IPA
    assert saved["endExtraMs"] == 300
    assert res.json()["text"] == "Hello there our friend!"


def test_concurrent_bumps_never_lose_a_write(data_dir: Path) -> None:
    write_lesson()
    threads = [
        threading.Thread(target=segment_ops.bump_end_extra, args=(LESSON_ID, 0)) for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert read_json()["segments"][0]["endExtraMs"] == 1500


def test_bump_requires_a_ready_lesson_and_a_valid_index(data_dir: Path) -> None:
    write_lesson(status="analyzing")
    with pytest.raises(segment_ops.InvalidState):
        segment_ops.bump_end_extra(LESSON_ID, 0)
    write_lesson()
    with pytest.raises(IndexError):
        segment_ops.bump_end_extra(LESSON_ID, 5)


def test_unknown_lesson_and_bad_index_error_codes(client: TestClient, spy: AnalyzeSpy) -> None:
    res = client.post(URL)
    assert (res.status_code, res.json()["code"]) == (404, "not_found")
    write_lesson()
    res = client.post(f"/lessons/{LESSON_ID}/segments/9/extend-end")
    assert (res.status_code, res.json()["code"]) == (404, "invalid_segment")
    write_lesson(status="queued")
    res = client.post(URL)
    assert (res.status_code, res.json()["code"]) == (409, "invalid_state")


def _write_stem(lesson: Lesson, seconds: float) -> None:
    """Stem vocal 16 kHz của khoảng bài ở đúng chỗ pipeline cache (không cần Demucs)."""
    start_ms = round(lesson.range.start * 1000)
    end_ms = round(lesson.range.end * 1000)
    folder = stems_dir(lesson.video_id, start_ms, end_ms)
    folder.mkdir(parents=True, exist_ok=True)
    tone = np.zeros(int(16000 * seconds), dtype=np.float32)
    write_audio(folder / "vocals.wav", np.stack([tone, tone]), 16000)


def test_real_analysis_rewrites_features_with_the_longer_window(
    client: TestClient, fake: FakeDeps, data_dir: Path
) -> None:
    write_lesson()
    _write_stem(store.load_lesson(LESSON_ID), 12.0)

    res = client.post(URL)

    assert res.status_code == 200
    with np.load(segment_features_path(LESSON_ID, 0)) as features:
        window = features["window"]
    # start 0.5 - 0.15 pad; end 3.8 + 0.15 pad + 0.3 mở rộng
    assert window.tolist() == pytest.approx([0.35, 4.25])
    assert_no_null(res.json())


def test_window_is_clamped_to_the_video_duration(client: TestClient, data_dir: Path) -> None:
    raw = make_lesson_dict()
    raw["durationSec"] = 4.0
    raw["range"] = {"start": 0.0, "end": 4.0}
    raw["segments"] = raw["segments"][:1]
    lesson = Lesson.model_validate(raw)
    store.save_lesson(lesson)
    _write_stem(lesson, 4.0)

    res = client.post(URL)

    assert res.status_code == 200
    with np.load(segment_features_path(LESSON_ID, 0)) as features:
        assert features["window"][1] == pytest.approx(4.0)

"""GET /system/status: model trong cache HF, hasKey/maskedKey, thư mục dữ liệu (SET-01/02)."""

import gc
import logging
import threading
import time
import weakref
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from audio_service import system_status
from audio_service.config import get_settings
from audio_service.main import create_app
from audio_service.system_status import WarmUp, model_cache_states

KEY = "sk-test-0123456789abcdefghij-WXYZ"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Cách ly: DATA_DIR, file .env và OPENAI_API_KEY đều nằm trong tmp."""
    data = tmp_path / "data"
    data.mkdir()
    env_file = tmp_path / "env"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("SHADOWENGLAB_ENV_FILE", str(env_file))
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    # undo của setenv khôi phục "không có", kể cả khi test ghi os.environ trực tiếp
    monkeypatch.delenv("OPENAI_API_KEY")
    get_settings.cache_clear()
    yield data
    get_settings.cache_clear()
    system_status.reset_warm_up()


def make_client() -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def use_cache(cached: dict[str, bool]) -> None:
    system_status.reset_warm_up(WarmUp(model_cache_states(check=lambda: cached)))


ALL = {"demucs": True, "whisper": True, "wav2vec2": True}


def test_cached_models_start_loading_and_uncached_are_missing(env: Path) -> None:
    use_cache({"demucs": True, "whisper": False, "wav2vec2": True})
    res = make_client().get("/system/status")
    assert res.status_code == 200
    assert res.json()["models"] == {
        "demucs": "loading",
        "whisper": "missing",
        "wav2vec2": "loading",
    }


def test_status_without_key_is_200_with_no_masked_key(env: Path) -> None:
    use_cache(ALL)
    res = make_client().get("/system/status")
    assert res.status_code == 200
    body = res.json()
    assert body["hasKey"] is False
    assert "maskedKey" not in body
    assert body["activeDataDir"] == str(env.resolve())


def test_status_with_key_shows_only_the_masked_key(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_cache(ALL)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    res = make_client().get("/system/status")
    body = res.json()
    assert body["hasKey"] is True
    assert body["maskedKey"] == "sk-…WXYZ"
    assert KEY not in res.text


def test_key_in_env_file_is_picked_up_without_restart(env: Path, tmp_path: Path) -> None:
    use_cache(ALL)
    client = make_client()
    assert client.get("/system/status").json()["hasKey"] is False
    (tmp_path / "env").write_text(f"FOO=1\nOPENAI_API_KEY={KEY}\n", encoding="utf-8")
    body = client.get("/system/status").json()
    assert body["hasKey"] is True and body["maskedKey"] == "sk-…WXYZ"


def test_empty_key_counts_as_no_key(env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    use_cache(ALL)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert make_client().get("/system/status").json()["hasKey"] is False


def test_status_shape_validates_against_the_contract(env: Path) -> None:
    from audio_service.contracts_gen import SystemStatus

    use_cache(ALL)
    SystemStatus.model_validate(make_client().get("/system/status").json())


def test_model_cache_check_is_cache_only_never_downloads() -> None:
    import inspect

    source = inspect.getsource(system_status.real_cache_check)
    assert source.count("download=False") == 3
    assert "download=True" not in source


# --- warm-up: nạp -> 1 suy luận -> giải phóng, từng model một dưới model_gate (D-18) -----------


class FakeModel:
    """Đại diện cho trọng số: test kiểm tra không ai còn giữ tham chiếu sau warm-up."""


def run_warm_up(
    gate: threading.Lock,
    loaders: dict[str, Callable[[], None]],
    state: WarmUp,
) -> threading.Thread:
    thread = system_status.start_warm_up(gate, loaders, warm_up=state)
    thread.join(10)
    assert not thread.is_alive()
    return thread


def test_warm_up_goes_loading_to_ready_one_model_at_a_time_under_the_gate() -> None:
    gate = threading.Lock()
    state = WarmUp(model_cache_states(check=lambda: ALL))
    guard = threading.Lock()
    running = 0
    peak = 0
    order: list[str] = []
    gate_held: list[bool] = []
    states_seen: list[dict[str, str]] = []
    refs: list[weakref.ref[FakeModel]] = []

    def make_loader(name: str) -> Callable[[], None]:
        def loader() -> None:
            nonlocal running, peak
            with guard:
                running += 1
                peak = max(peak, running)
            gate_held.append(gate.locked())
            states_seen.append(state.states())
            order.append(name)
            model = FakeModel()
            refs.append(weakref.ref(model))
            time.sleep(0.02)
            del model  # giải phóng ngay trong loader
            with guard:
                running -= 1

        return loader

    run_warm_up(gate, {n: make_loader(n) for n in system_status.MODEL_ORDER}, state)
    assert order == ["demucs", "whisper", "wav2vec2"]
    assert peak == 1
    assert gate_held == [True, True, True]
    assert states_seen[0] == {"demucs": "loading", "whisper": "loading", "wav2vec2": "loading"}
    assert states_seen[1] == {"demucs": "ready", "whisper": "loading", "wav2vec2": "loading"}
    assert states_seen[2] == {"demucs": "ready", "whisper": "ready", "wav2vec2": "loading"}
    assert state.states() == {"demucs": "ready", "whisper": "ready", "wav2vec2": "ready"}
    assert not gate.locked()
    gc.collect()
    assert [r() for r in refs] == [None, None, None]  # không model nào còn nằm trong RAM


def test_warm_up_waits_while_a_lesson_job_holds_the_model_gate() -> None:
    gate = threading.Lock()
    state = WarmUp(model_cache_states(check=lambda: ALL))
    called: list[str] = []
    loaders = {n: (lambda n=n: called.append(n)) for n in system_status.MODEL_ORDER}
    with gate:  # một job tạo bài đang ở bước model
        thread = system_status.start_warm_up(gate, loaders, warm_up=state)
        time.sleep(0.2)
        assert called == []
        assert set(state.states().values()) == {"loading"}
    thread.join(10)
    assert called == ["demucs", "whisper", "wav2vec2"]
    assert set(state.states().values()) == {"ready"}


def test_a_failing_loader_marks_only_that_model_missing_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    gate = threading.Lock()
    state = WarmUp(model_cache_states(check=lambda: ALL))
    called: list[str] = []

    def boom() -> None:
        called.append("whisper")
        raise RuntimeError("không nạp được")

    loaders: dict[str, Callable[[], None]] = {
        "demucs": lambda: called.append("demucs"),
        "whisper": boom,
        "wav2vec2": lambda: called.append("wav2vec2"),
    }
    with caplog.at_level(logging.ERROR):
        run_warm_up(gate, loaders, state)
    assert state.states() == {"demucs": "ready", "whisper": "missing", "wav2vec2": "ready"}
    assert called == ["demucs", "whisper", "wav2vec2"]  # lỗi một model không dừng các model sau
    assert not gate.locked()  # cổng luôn được nhả
    assert any("whisper" in r.getMessage() and r.exc_info for r in caplog.records)


def test_models_missing_from_the_cache_are_skipped_not_loaded() -> None:
    gate = threading.Lock()
    state = WarmUp(model_cache_states(check=lambda: {"demucs": True, "wav2vec2": True}))
    called: list[str] = []
    loaders = {n: (lambda n=n: called.append(n)) for n in system_status.MODEL_ORDER}
    run_warm_up(gate, loaders, state)
    assert called == ["demucs", "wav2vec2"]
    assert state.states() == {"demucs": "ready", "whisper": "missing", "wav2vec2": "ready"}


def test_warm_up_thread_is_a_daemon() -> None:
    gate = threading.Lock()
    state = WarmUp(model_cache_states(check=lambda: {}))
    thread = run_warm_up(gate, {}, state)
    assert thread.daemon is True


def test_status_endpoint_reflects_warm_up_progress(env: Path) -> None:
    state = WarmUp(model_cache_states(check=lambda: ALL))
    system_status.reset_warm_up(state)
    client = make_client()
    assert client.get("/system/status").json()["models"]["whisper"] == "loading"
    state.set("whisper", "ready")
    assert client.get("/system/status").json()["models"]["whisper"] == "ready"


def test_real_loaders_cover_the_three_models_in_the_locked_order() -> None:
    assert list(system_status.real_loaders()) == ["demucs", "whisper", "wav2vec2"]


def test_demucs_loader_loads_infers_then_frees_even_when_inference_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from audio_service.lesson import separate

    events: list[str] = []
    monkeypatch.setattr(separate, "pick_device", lambda: "cpu")
    monkeypatch.setattr(
        separate, "load_separator", lambda device: events.append("load") or object()
    )
    monkeypatch.setattr(
        separate, "separate_vocals", lambda *_a: events.append("infer") or (None, None)
    )
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: events.append("free"))
    system_status.real_loaders()["demucs"]()
    assert events == ["load", "infer", "free"]

    events.clear()

    def fail(*_a: object) -> None:
        events.append("infer")
        raise RuntimeError("hỏng")

    monkeypatch.setattr(separate, "separate_vocals", fail)
    with pytest.raises(RuntimeError):
        system_status.real_loaders()["demucs"]()
    assert events == ["load", "infer", "free"]


def test_demucs_loader_keeps_the_real_error_when_the_cpu_fallback_fails_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from audio_service.lesson import separate

    monkeypatch.setattr(separate, "pick_device", lambda: "mps")

    def load(device: str) -> object:
        if device == "cpu":
            raise OSError("không nạp được model CPU")
        return object()

    def fail(*_a: object) -> None:
        raise RuntimeError("MPS hỏng")

    monkeypatch.setattr(separate, "load_separator", load)
    monkeypatch.setattr(separate, "separate_vocals", fail)
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: None)
    with pytest.raises(OSError, match="CPU"):
        system_status.real_loaders()["demucs"]()


def test_whisper_loader_transcribes_silence_then_releases_the_holder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys
    import types

    from audio_service.lesson import separate, transcribe
    from audio_service.models import WHISPER_REPO

    events: list[str] = []

    def fake_transcribe(audio: object, **kwargs: object) -> dict[str, object]:
        assert getattr(audio, "shape", None) == (16000,)  # 1 s im lặng
        assert kwargs["path_or_hf_repo"] == WHISPER_REPO
        events.append("infer")
        return {"segments": []}

    fake_module = types.SimpleNamespace(transcribe=fake_transcribe)
    monkeypatch.setitem(sys.modules, "mlx_whisper", fake_module)
    monkeypatch.setattr(transcribe, "release_whisper", lambda: events.append("release"))
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: events.append("free"))
    system_status.real_loaders()["whisper"]()
    assert events == ["infer", "release", "free"]


def test_wav2vec2_loader_loads_infers_then_frees(monkeypatch: pytest.MonkeyPatch) -> None:
    from audio_service.lesson import features, separate

    events: list[str] = []
    monkeypatch.setattr(separate, "pick_device", lambda: "cpu")
    monkeypatch.setattr(
        features, "load_ppg_model", lambda device: events.append("load") or object()
    )
    monkeypatch.setattr(features, "compute_ppg", lambda *_a: events.append("infer"))
    monkeypatch.setattr(separate, "free_accelerator_memory", lambda: events.append("free"))
    system_status.real_loaders()["wav2vec2"]()
    assert events == ["load", "infer", "free"]


# --- lifespan khởi động warm-up -----------------------------------------------------------------


def test_lifespan_starts_warm_up_with_the_runner_model_gate_by_default(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[threading.Lock] = []

    def fake_start(gate: threading.Lock, *_a: object, **_k: object) -> threading.Thread:
        calls.append(gate)
        return threading.Thread()

    monkeypatch.setattr(system_status, "start_warm_up", fake_start)
    app = create_app()  # không inject deps -> warm-up bật
    with TestClient(app, base_url="http://127.0.0.1"):
        assert calls == [app.state.runner.model_gate]


def test_lifespan_with_injected_deps_never_warms_up_unless_asked(
    env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from audio_service.lesson import pipeline

    calls: list[object] = []
    monkeypatch.setattr(
        system_status, "start_warm_up", lambda *a, **k: calls.append(a) or threading.Thread()
    )
    deps = pipeline.default_deps()
    with TestClient(create_app(deps=deps), base_url="http://127.0.0.1"):
        assert calls == []
    with TestClient(create_app(deps=deps, warm_up=True), base_url="http://127.0.0.1"):
        assert len(calls) == 1
    with TestClient(create_app(warm_up=False), base_url="http://127.0.0.1"):
        assert len(calls) == 1

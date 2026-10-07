"""GET /system/status: model trong cache HF, hasKey/maskedKey, thư mục dữ liệu (SET-01/02)."""

from collections.abc import Iterator
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

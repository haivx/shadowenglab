"""GET/PUT /settings và thứ tự ưu tiên dataDir (SET-04, D-10, D-12, 02-01 mục G)."""

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from audio_service import config as cfg
from audio_service.main import create_app

BAD_DIR_BODY = {
    "code": "invalid_settings",
    "message": "Thư mục không tồn tại hoặc không ghi được.",
}


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    data = tmp_path / "env-data"
    data.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data))
    cfg.get_settings.cache_clear()
    yield data.resolve()
    cfg.get_settings.cache_clear()


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    return TestClient(create_app(), base_url="http://127.0.0.1")


def settings_json() -> Path:
    return cfg.settings_file_path()


def valid_body(data_dir: Path, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "playbackRate": 0.75,
        "repeat": 2,
        "recordFactor": 2.0,
        "dataDir": str(data_dir),
        "accent": "US",
    }
    body.update(over)
    return body


def test_tests_are_isolated_from_the_real_machine(tmp_path: Path) -> None:
    assert os.environ["SHADOWENGLAB_CONFIG_DIR"] == str(cfg.config_dir())
    assert Path.home() not in cfg.config_dir().parents
    assert cfg.settings_file_path() == cfg.config_dir() / "settings.json"
    assert os.environ["SHADOWENGLAB_ENV_FILE"]
    assert "OPENAI_API_KEY" not in os.environ


def test_config_dir_defaults_to_dot_config_when_not_overridden(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("SHADOWENGLAB_CONFIG_DIR")
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cfg.config_dir() == tmp_path / ".config" / "shadowenglab"


def test_get_without_a_file_returns_defaults_with_the_active_data_dir(
    client: TestClient, data_dir: Path
) -> None:
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json() == {
        "playbackRate": 1,
        "repeat": 1,
        "recordFactor": 1.5,
        "dataDir": str(cfg.data_root()),
        "accent": "US",
    }
    assert cfg.data_root() == data_dir
    assert not settings_json().exists()  # GET không tạo file


def test_data_dir_precedence_file_over_env_over_default(
    data_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved = tmp_path / "saved"
    saved.mkdir()
    settings_json().write_text(json.dumps({"dataDir": str(saved)}), encoding="utf-8")
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == saved.resolve()  # settings.json thắng DATA_DIR

    settings_json().write_text(json.dumps({"repeat": 2}), encoding="utf-8")
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == data_dir  # file không có khoá dataDir -> DATA_DIR

    settings_json().unlink()
    monkeypatch.delenv("DATA_DIR")
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == (tmp_path / "shadowenglab-data").resolve()  # không có gì -> mặc định


@pytest.mark.parametrize("bad", ["relative/dir", "", 42, None, "~/nope"])
def test_unusable_saved_data_dir_is_ignored(data_dir: Path, bad: object) -> None:
    settings_json().write_text(json.dumps({"dataDir": bad}), encoding="utf-8")
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == data_dir


def test_corrupt_settings_file_does_not_break_data_root(data_dir: Path) -> None:
    settings_json().write_text("{not json", encoding="utf-8")
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == data_dir


def test_put_saves_and_get_returns_it(client: TestClient, data_dir: Path) -> None:
    body = valid_body(data_dir)
    res = client.put("/settings", json=body)
    assert res.status_code == 200
    assert res.json() == body
    assert json.loads(settings_json().read_text(encoding="utf-8")) == body
    assert client.get("/settings").json() == body


def test_put_writes_atomically_without_leftovers(client: TestClient, data_dir: Path) -> None:
    client.put("/settings", json=valid_body(data_dir))
    client.put("/settings", json=valid_body(data_dir, repeat=3))
    assert sorted(p.name for p in cfg.config_dir().iterdir()) == ["settings.json"]


def test_put_new_data_dir_applies_only_after_restart(
    client: TestClient, data_dir: Path, tmp_path: Path
) -> None:
    new_dir = tmp_path / "elsewhere"
    new_dir.mkdir()
    (data_dir / "keep.txt").write_text("old data stays", encoding="utf-8")
    assert client.put("/settings", json=valid_body(new_dir)).status_code == 200
    # chưa restart: thư mục đang dùng không đổi, file không bị chuyển (D-12)
    assert cfg.data_root() == data_dir
    assert client.get("/system/status").json()["activeDataDir"] == str(data_dir)
    assert (data_dir / "keep.txt").read_text(encoding="utf-8") == "old data stays"
    assert list(new_dir.iterdir()) == []
    # restart giả lập = xoá cache phân giải
    cfg.get_settings.cache_clear()
    assert cfg.data_root() == new_dir.resolve()
    assert client.get("/system/status").json()["activeDataDir"] == str(new_dir.resolve())


def test_put_data_dir_relative_is_422_invalid_settings(client: TestClient, data_dir: Path) -> None:
    res = client.put("/settings", json=valid_body(data_dir, dataDir="some/relative"))
    assert res.status_code == 422
    assert res.json() == BAD_DIR_BODY
    assert not settings_json().exists()


def test_put_data_dir_missing_is_422_invalid_settings(
    client: TestClient, tmp_path: Path, data_dir: Path
) -> None:
    res = client.put("/settings", json=valid_body(data_dir, dataDir=str(tmp_path / "ghost")))
    assert res.status_code == 422
    assert res.json() == BAD_DIR_BODY
    assert str(tmp_path) not in res.text


def test_put_data_dir_that_is_a_file_is_422(
    client: TestClient, tmp_path: Path, data_dir: Path
) -> None:
    a_file = tmp_path / "plain.txt"
    a_file.write_text("x", encoding="utf-8")
    res = client.put("/settings", json=valid_body(data_dir, dataDir=str(a_file)))
    assert res.status_code == 422
    assert res.json() == BAD_DIR_BODY


@pytest.mark.skipif(os.geteuid() == 0, reason="root ghi được vào mọi thư mục")
def test_put_data_dir_not_writable_is_422(
    client: TestClient, tmp_path: Path, data_dir: Path
) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        res = client.put("/settings", json=valid_body(data_dir, dataDir=str(locked)))
    finally:
        locked.chmod(0o700)
    assert res.status_code == 422
    assert res.json() == BAD_DIR_BODY


@pytest.mark.parametrize(
    "over",
    [
        {"repeat": 4},
        {"repeat": 0},
        {"accent": "UK"},
        {"playbackRate": 2},
        {"recordFactor": 0.5},
    ],
)
def test_put_contract_violations_are_422_api_error(
    client: TestClient, data_dir: Path, over: dict[str, Any]
) -> None:
    res = client.put("/settings", json=valid_body(data_dir, **over))
    assert res.status_code == 422
    assert res.json() == {"code": "invalid_request", "message": "Dữ liệu gửi lên không hợp lệ."}
    assert not settings_json().exists()


def test_corrupt_settings_file_gives_defaults_and_put_overwrites_it(
    client: TestClient, data_dir: Path
) -> None:
    settings_json().write_text("{not json", encoding="utf-8")
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json()["repeat"] == 1 and res.json()["dataDir"] == str(data_dir)

    body = valid_body(data_dir, repeat=3)
    assert client.put("/settings", json=body).status_code == 200
    assert json.loads(settings_json().read_text(encoding="utf-8")) == body


def test_settings_file_failing_the_contract_gives_defaults(
    client: TestClient, data_dir: Path
) -> None:
    bad = valid_body(data_dir, accent="UK")
    settings_json().write_text(json.dumps(bad), encoding="utf-8")
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json()["accent"] == "US" and res.json()["repeat"] == 1


def test_read_and_default_helpers(data_dir: Path) -> None:
    from audio_service import settings_store

    assert settings_store.default_settings().data_dir == str(cfg.data_root())
    assert settings_store.read_settings() == settings_store.default_settings()
    with pytest.raises(settings_store.InvalidDataDirError):
        settings_store.validate_data_dir("not/absolute")
    assert settings_store.validate_data_dir(str(data_dir)) == data_dir

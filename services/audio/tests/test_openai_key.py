"""POST /settings/openai-key/check, set_openai_key và .env (SET-02/03, D-11, T-02-30/31)."""

import logging
import os
import re
import stat
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from audio_service import secrets_env
from audio_service.main import create_app
from audio_service.routers import settings as settings_router

KEY = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
MASKED = "sk-…ABCD"
OTHER_KEY = "sk-live-ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210zyxw"


class Upstream:
    """Giả lập OpenAI qua httpx.MockTransport và ghi lại mọi request."""

    def __init__(self, responder: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._responder = responder

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responder(request)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def status_upstream(code: int) -> Upstream:
    return Upstream(lambda _r: httpx.Response(code, json={"data": []}))


def failing_upstream() -> Upstream:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("không có mạng", request=request)

    return Upstream(boom)


@pytest.fixture
def env_file() -> Path:
    return Path(os.environ["SHADOWENGLAB_ENV_FILE"])


@pytest.fixture
def make_client() -> Iterator[Callable[[Upstream], TestClient]]:
    apps = []

    def build(upstream: Upstream) -> TestClient:
        app = create_app()
        app.dependency_overrides[settings_router.get_http_client] = upstream.client
        apps.append(app)
        return TestClient(app, base_url="http://127.0.0.1")

    yield build


def check(client: TestClient, body: dict[str, object] | None = None) -> httpx.Response:
    return client.post("/settings/openai-key/check", json=body if body is not None else {})


# --- secrets_env -----------------------------------------------------------------------------


def test_set_openai_key_keeps_other_lines_sets_mode_600_and_hot_loads(env_file: Path) -> None:
    env_file.write_text("FOO=1\n# comment\nDATA_DIR=~/x\n", encoding="utf-8")
    env_file.chmod(0o644)
    secrets_env.set_openai_key(KEY)
    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines[:3] == ["FOO=1", "# comment", "DATA_DIR=~/x"]
    assert lines.count(f"OPENAI_API_KEY={KEY}") == 1
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert os.environ["OPENAI_API_KEY"] == KEY


def test_set_openai_key_replaces_an_existing_key_without_duplicating(env_file: Path) -> None:
    env_file.write_text(f"OPENAI_API_KEY={OTHER_KEY}\nFOO=1\n", encoding="utf-8")
    secrets_env.set_openai_key(KEY)
    text = env_file.read_text(encoding="utf-8")
    assert text.count("OPENAI_API_KEY=") == 1
    assert OTHER_KEY not in text and KEY in text and "FOO=1" in text


def test_set_openai_key_creates_a_missing_file_with_mode_600(env_file: Path) -> None:
    assert not env_file.exists()
    secrets_env.set_openai_key(KEY)
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert secrets_env.get_openai_key() == KEY


BAD_KEYS = [
    "sk-abc",  # quá ngắn
    "sk-a\nEVIL=1" + "x" * 30,  # newline: chèn thêm biến vào .env
    "sk-a=b" + "x" * 30,  # dấu =
    "sk- abc" + "x" * 30,  # khoảng trắng
    "sk-abc" + "x" * 30 + "\n",  # newline cuối
    "sk-abc\tdef" + "x" * 30,
    "sk-" + "é" * 30,
    "s" * 257,  # quá dài
]


@pytest.mark.parametrize("bad", BAD_KEYS)
def test_set_openai_key_rejects_malformed_keys_before_touching_anything(
    bad: str, env_file: Path
) -> None:
    with pytest.raises(secrets_env.InvalidKeyError) as err:
        secrets_env.set_openai_key(bad)
    assert bad not in str(err.value)
    assert not env_file.exists()
    assert "OPENAI_API_KEY" not in os.environ


def test_key_pattern_accepts_the_usual_key_alphabet() -> None:
    assert secrets_env.KEY_RE.fullmatch(KEY)
    assert secrets_env.KEY_RE.fullmatch("sk-" + "a_-B9" * 6)


def test_mask_key_shows_three_and_four_characters() -> None:
    assert secrets_env.mask_key(KEY) == MASKED
    assert secrets_env.mask_key("short") == "…"


@pytest.mark.parametrize(
    ("code", "expected"),
    [(200, True), (401, False), (403, False), (429, None), (500, None), (503, None)],
)
def test_check_openai_key_maps_status_codes(code: int, expected: bool | None) -> None:
    upstream = status_upstream(code)
    with upstream.client() as client:
        assert secrets_env.check_openai_key(KEY, client) is expected
    (request,) = upstream.requests
    assert request.method == "GET"
    assert str(request.url) == "https://api.openai.com/v1/models"
    assert request.headers["authorization"] == f"Bearer {KEY}"


def test_check_openai_key_network_error_is_none() -> None:
    with failing_upstream().client() as client:
        assert secrets_env.check_openai_key(KEY, client) is None


# --- POST /settings/openai-key/check ---------------------------------------------------------


def test_valid_key_is_saved_to_env_and_hot_loaded(
    make_client: Callable[[Upstream], TestClient], env_file: Path
) -> None:
    env_file.write_text("FOO=1\n", encoding="utf-8")
    upstream = status_upstream(200)
    client = make_client(upstream)
    res = check(client, {"apiKey": KEY})
    assert res.status_code == 200
    assert res.json() == {"valid": True, "saved": True, "maskedKey": MASKED}
    assert KEY not in res.text
    assert f"OPENAI_API_KEY={KEY}" in env_file.read_text(encoding="utf-8")
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert os.environ["OPENAI_API_KEY"] == KEY
    status = client.get("/system/status").json()  # nạp nóng, không restart
    assert status["hasKey"] is True and status["maskedKey"] == MASKED
    assert KEY not in client.get("/system/status").text


def test_rejected_key_is_not_written(
    make_client: Callable[[Upstream], TestClient], env_file: Path
) -> None:
    for code in (401, 403):
        res = check(make_client(status_upstream(code)), {"apiKey": KEY})
        assert res.status_code == 200
        assert res.json() == {"valid": False, "saved": False, "reason": "invalid"}
        assert KEY not in res.text
    assert not env_file.exists()
    assert "OPENAI_API_KEY" not in os.environ


@pytest.mark.parametrize("upstream_factory", [lambda: status_upstream(503), failing_upstream])
def test_network_problem_is_null_and_not_written(
    make_client: Callable[[Upstream], TestClient],
    env_file: Path,
    upstream_factory: Callable[[], Upstream],
) -> None:
    res = check(make_client(upstream_factory()), {"apiKey": KEY})
    assert res.status_code == 200
    assert res.json() == {"valid": None, "saved": False, "reason": "network"}
    assert not env_file.exists()
    assert "OPENAI_API_KEY" not in os.environ


@pytest.mark.parametrize("bad", BAD_KEYS + ["   "])
def test_malformed_key_never_reaches_the_network_or_the_env_file(
    make_client: Callable[[Upstream], TestClient], env_file: Path, bad: str
) -> None:
    upstream = status_upstream(200)
    res = check(make_client(upstream), {"apiKey": bad})
    assert res.status_code == 200
    assert res.json() == {"valid": False, "saved": False, "reason": "invalid"}
    assert upstream.requests == []
    assert not env_file.exists()
    assert "OPENAI_API_KEY" not in os.environ
    assert bad not in res.text


@pytest.mark.parametrize("body", [{}, {"apiKey": ""}])
def test_empty_request_without_a_saved_key_is_no_key(
    make_client: Callable[[Upstream], TestClient], env_file: Path, body: dict[str, object]
) -> None:
    upstream = status_upstream(200)
    res = check(make_client(upstream), body)
    assert res.status_code == 200
    assert res.json() == {"valid": None, "saved": False, "reason": "no_key"}
    assert upstream.requests == []
    assert not env_file.exists()


def test_empty_request_tests_the_saved_key_without_rewriting_the_file(
    make_client: Callable[[Upstream], TestClient], env_file: Path
) -> None:
    env_file.write_text(f"OPENAI_API_KEY={OTHER_KEY}\nFOO=1\n", encoding="utf-8")
    before = env_file.read_text(encoding="utf-8")
    upstream = status_upstream(200)
    res = check(make_client(upstream), {})
    assert res.status_code == 200
    assert res.json() == {"valid": True, "saved": True, "maskedKey": "sk-…zyxw"}
    assert upstream.requests[0].headers["authorization"] == f"Bearer {OTHER_KEY}"
    assert env_file.read_text(encoding="utf-8") == before
    assert OTHER_KEY not in res.text


def test_saved_key_rejected_by_openai_reports_invalid(
    make_client: Callable[[Upstream], TestClient], env_file: Path
) -> None:
    env_file.write_text(f"OPENAI_API_KEY={OTHER_KEY}\n", encoding="utf-8")
    res = check(make_client(status_upstream(401)), {})
    assert res.json() == {"valid": False, "saved": False, "reason": "invalid"}


def test_a_newly_typed_key_replaces_the_saved_one_only_when_valid(
    make_client: Callable[[Upstream], TestClient], env_file: Path
) -> None:
    env_file.write_text(f"OPENAI_API_KEY={OTHER_KEY}\n", encoding="utf-8")
    check(make_client(status_upstream(401)), {"apiKey": KEY})
    assert OTHER_KEY in env_file.read_text(encoding="utf-8")
    check(make_client(status_upstream(200)), {"apiKey": KEY})
    text = env_file.read_text(encoding="utf-8")
    assert KEY in text and OTHER_KEY not in text


def test_write_failure_is_a_fixed_500_that_does_not_echo_the_key(
    make_client: Callable[[Upstream], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(key: str) -> None:
        raise OSError(f"disk full while writing {key}")

    monkeypatch.setattr(secrets_env, "set_openai_key", explode)
    res = check(make_client(status_upstream(200)), {"apiKey": KEY})
    assert res.status_code == 500
    assert res.json()["code"] == "internal_error"
    assert KEY not in res.text


@pytest.mark.parametrize(
    "scenario",
    [
        ("ok", lambda: status_upstream(200)),
        ("401", lambda: status_upstream(401)),
        ("503", lambda: status_upstream(503)),
        ("down", failing_upstream),
    ],
    ids=lambda s: s[0] if isinstance(s, tuple) else str(s),
)
def test_the_key_never_appears_in_any_log_record(
    make_client: Callable[[Upstream], TestClient],
    caplog: pytest.LogCaptureFixture,
    scenario: tuple[str, Callable[[], Upstream]],
) -> None:
    caplog.set_level(logging.DEBUG)
    client = make_client(scenario[1]())
    res = check(client, {"apiKey": KEY})
    client.get("/system/status")
    assert KEY not in res.text
    assert KEY not in caplog.text
    assert not [r for r in caplog.records if KEY in r.getMessage() or KEY in repr(r.args)]


def test_missing_key_never_blocks_the_rest_of_the_api(
    make_client: Callable[[Upstream], TestClient],
) -> None:
    client = make_client(status_upstream(200))
    assert client.get("/system/status").json()["hasKey"] is False
    assert client.get("/settings").status_code == 200
    assert client.get("/lessons").status_code == 200
    assert client.get("/health").status_code == 200


def test_no_openai_sdk_is_imported_anywhere_in_the_service() -> None:
    root = Path(secrets_env.__file__).parent
    pattern = re.compile(r"^\s*(import|from)\s+openai\b", re.MULTILINE)
    offenders = [p.name for p in root.rglob("*.py") if pattern.search(p.read_text("utf-8"))]
    assert offenders == []  # D-23: chỉ httpx

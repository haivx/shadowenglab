"""Test cho scripts/check_deps.sh (stub PATH) và audio_service.setup_models (mock)."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

from audio_service import models, setup_models
from audio_service.setup_models import CheckResult

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK_DEPS = REPO_ROOT / "scripts" / "check_deps.sh"
ALL_TOOLS = ("ffmpeg", "espeak-ng", "uv", "pnpm", "node")


def _stub(path: Path, body: str) -> None:
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_stub_dir(
    root: Path, tools: tuple[str, ...] = ALL_TOOLS, node_version: str = "v24.16.0"
) -> Path:
    stub = root / "stub"
    stub.mkdir()
    for tool in tools:
        if tool == "node":
            _stub(stub / "node", f'echo "{node_version}"')
        else:
            _stub(stub / tool, f'echo "{tool} stub 1.0"')
    return stub


def _run_check_deps(stub: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": f"{stub}:/usr/bin:/bin"}
    return subprocess.run(
        ["sh", str(CHECK_DEPS)], capture_output=True, text=True, env=env, check=False
    )


# (a) mọi tool có, Node đủ phiên bản -> exit 0
def test_check_deps_all_present(tmp_path: Path) -> None:
    proc = _run_check_deps(_make_stub_dir(tmp_path))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "THIẾU" not in proc.stdout
    assert "CŨ" not in proc.stdout


# (b) thiếu ffmpeg và espeak-ng -> exit 1 và in lệnh brew đúng
def test_check_deps_missing_ffmpeg_and_espeak(tmp_path: Path) -> None:
    stub = _make_stub_dir(tmp_path, tools=("uv", "pnpm", "node"))
    proc = _run_check_deps(stub)
    assert proc.returncode == 1
    assert "brew install ffmpeg espeak-ng" in proc.stdout
    assert "make setup dừng" in proc.stdout


def test_check_deps_prints_only_missing_subset(tmp_path: Path) -> None:
    stub = _make_stub_dir(tmp_path, tools=("ffmpeg", "uv", "pnpm", "node"))
    proc = _run_check_deps(stub)
    assert proc.returncode == 1
    assert "brew install espeak-ng" in proc.stdout
    assert "brew install ffmpeg" not in proc.stdout
    assert "brew install uv" not in proc.stdout


def test_check_deps_no_tools_lists_every_hint(tmp_path: Path) -> None:
    stub = _make_stub_dir(tmp_path, tools=())
    proc = _run_check_deps(stub)
    assert proc.returncode == 1
    for hint in ("brew install ffmpeg espeak-ng", "brew install uv", "brew install node", "pnpm@"):
        assert hint in proc.stdout


# (c) Node cũ hơn NODE_MIN (22.13) -> exit 1 kèm gợi ý node
@pytest.mark.parametrize(
    ("version", "expected_rc"),
    [
        ("v20.11.0", 1),
        ("v22.12.9", 1),
        ("v22.13.0", 0),
        ("v22.20.0", 0),
        ("v24.16.0", 0),
        ("v100.0.0", 0),
    ],
)
def test_check_deps_node_minimum(tmp_path: Path, version: str, expected_rc: int) -> None:
    proc = _run_check_deps(_make_stub_dir(tmp_path, node_version=version))
    assert proc.returncode == expected_rc, proc.stdout
    if expected_rc == 1:
        assert "brew install node" in proc.stdout


# (d) brew/npm stub ghi marker khi bị gọi -> sau khi thiếu tool, marker không tồn tại
def test_check_deps_never_runs_an_installer(tmp_path: Path) -> None:
    marker = tmp_path / "installer-ran"
    stub = _make_stub_dir(tmp_path, tools=("uv", "node"))
    for installer in ("brew", "npm", "curl", "pip", "uv-install"):
        _stub(stub / installer, f'touch "{marker}"')
    proc = _run_check_deps(stub)
    assert proc.returncode == 1
    assert "brew install ffmpeg espeak-ng" in proc.stdout
    assert not marker.exists()


def test_check_deps_script_has_no_installer_invocation() -> None:
    # Dòng lệnh thật sự (không tính dòng echo/comment) không được gọi brew/npm/curl.
    for line in CHECK_DEPS.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(("#", "echo", "row", "printf")):
            continue
        assert not stripped.startswith(("brew ", "npm ", "curl ", "pip ")), line


# (e) setup_models.main với check mock
def _ok(name: str, *, required: bool = True) -> CheckResult:
    return CheckResult(name, True, "ok", required)


def _patch_all_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_models, "ensure_hf_snapshot", lambda repo, patterns, *, download: _ok(repo)
    )
    monkeypatch.setattr(setup_models, "ensure_demucs", lambda *, download: _ok("demucs"))
    monkeypatch.setattr(setup_models, "check_parselmouth", lambda: _ok("parselmouth"))
    monkeypatch.setattr(setup_models, "check_ffmpeg", lambda: _ok("ffmpeg"))
    monkeypatch.setattr(setup_models, "check_mps", lambda: _ok("mps", required=False))


def test_main_all_ok_returns_zero(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _patch_all_ok(monkeypatch)
    assert setup_models.main(["--no-download"]) == 0
    out = capsys.readouterr().out
    assert models.WHISPER_REPO in out
    assert models.PPG_REPO in out


def test_main_ffmpeg_failure_returns_one(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _patch_all_ok(monkeypatch)
    monkeypatch.setattr(setup_models, "check_ffmpeg", lambda: CheckResult("ffmpeg", False, "thiếu"))
    assert setup_models.main(["--no-download"]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_mps_failure_only_warns(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _patch_all_ok(monkeypatch)
    monkeypatch.setattr(
        setup_models, "check_mps", lambda: CheckResult("mps", False, "không có", required=False)
    )
    assert setup_models.main(["--no-download"]) == 0
    assert "WARN" in capsys.readouterr().out


def test_main_passes_download_flag_and_locked_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_all_ok(monkeypatch)
    calls: list[tuple[str, tuple[str, ...] | None, bool]] = []

    def fake_snapshot(repo, patterns, *, download):
        calls.append((repo, tuple(patterns) if patterns is not None else None, download))
        return _ok(repo)

    monkeypatch.setattr(setup_models, "ensure_hf_snapshot", fake_snapshot)
    assert setup_models.main([]) == 0
    assert calls == [
        (models.WHISPER_REPO, None, True),
        (models.PPG_REPO, models.PPG_ALLOW_PATTERNS, True),
    ]
    calls.clear()
    assert setup_models.main(["--no-download"]) == 0
    assert all(download is False for _, _, download in calls)


def test_no_flag_overrides_model_ids() -> None:
    with pytest.raises(SystemExit):
        setup_models.main(["--whisper-repo", "evil/model"])


def test_ensure_hf_snapshot_failure_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import huggingface_hub

    def boom(**_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", boom)
    res = setup_models.ensure_hf_snapshot("a/b", None, download=False)
    assert not res.ok
    assert "offline" in res.detail


def test_ensure_hf_snapshot_uses_local_files_only_when_not_downloading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import huggingface_hub

    seen: dict[str, object] = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return "/cache/x"

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake)
    res = setup_models.ensure_hf_snapshot("a/b", ("config.json",), download=False)
    assert res.ok
    assert seen["local_files_only"] is True
    assert seen["allow_patterns"] == ["config.json"]
    setup_models.ensure_hf_snapshot("a/b", None, download=True)
    assert seen["local_files_only"] is False


def test_format_status_table_marks_levels() -> None:
    table = setup_models.format_status_table(
        [
            CheckResult("a", True, "x"),
            CheckResult("b", False, "y"),
            CheckResult("c", False, "z", required=False),
        ]
    )
    assert "OK" in table
    assert "FAIL" in table
    assert "WARN" in table


# (f) parselmouth thật
def test_check_parselmouth_real() -> None:
    res = setup_models.check_parselmouth()
    assert res.ok, res.detail


# (g) hằng số model khớp đúng ba id đã khoá (guard governance)
def test_locked_model_ids_are_exact() -> None:
    assert models.WHISPER_REPO == "mlx-community/whisper-large-v3-turbo"
    assert models.PPG_REPO == "facebook/wav2vec2-lv-60-espeak-cv-ft"
    assert models.DEMUCS_MODEL == "htdemucs"
    assert models.DEMUCS_HF_REPO == "adefossez/HTDemucs"
    assert models.PPG_ALLOW_PATTERNS == (
        "config.json",
        "preprocessor_config.json",
        "vocab.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "pytorch_model.bin",
    )


def test_no_other_module_hardcodes_model_ids() -> None:
    src = Path(setup_models.__file__).parent
    for path in src.rglob("*.py"):
        if path.name == "models.py":
            continue
        text = path.read_text()
        for literal in (models.WHISPER_REPO, models.PPG_REPO, models.DEMUCS_HF_REPO):
            assert literal not in text, f"{path.name} hard-codes {literal}"

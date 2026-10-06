"""Drift gate D-20: `scripts/contracts_check.sh` phải xanh khi artifact khớp Zod và đỏ khi lệch."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "contracts_check.sh"
COMMITTED_SCHEMA = ROOT / "packages/contracts/schema/contracts.schema.json"


def _run_gate(extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(
        ["sh", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_no_drift() -> None:
    result = _run_gate()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CONTRACT DRIFT" not in result.stdout


def test_detects_drift(tmp_path: Path) -> None:
    """Sửa một giá trị trong bản schema đã commit (bản sao) thì gate phải thoát 1."""
    text = COMMITTED_SCHEMA.read_text(encoding="utf-8")
    assert '"type": "object"' in text, "schema không còn chứa mốc dùng để làm lệch"
    drifted = tmp_path / "contracts.schema.json"
    drifted.write_text(text.replace('"type": "object"', '"type":  "object"', 1), encoding="utf-8")

    result = _run_gate({"CONTRACTS_SCHEMA_COMMITTED": str(drifted)})

    assert result.returncode == 1, result.stdout + result.stderr
    assert "CONTRACT DRIFT" in result.stdout

"""Round-trip D-21: Zod -> JSON Schema (2020-12) -> pydantic -> JSON -> Zod, phải bằng nhau."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter

from audio_service import contracts_gen

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "packages/contracts/schema/contracts.schema.json").read_text("utf-8"))
FIXTURE_DIR = ROOT / "packages/contracts/fixtures"


def _cases() -> list[tuple[str, str, Any]]:
    cases: list[tuple[str, str, Any]] = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        for case in json.loads(path.read_text("utf-8")):
            cases.append((path.stem, case["name"], case["data"]))
    return cases


CASES = _cases()


def _run_zod(type_name: str, payload: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pnpm",
            "--silent",
            "--filter",
            "@shadowenglab/contracts",
            "exec",
            "tsx",
            "src/cli-parse.ts",
            type_name,
        ],
        cwd=ROOT,
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def zod_parse(type_name: str, payload: Any) -> Any:
    """Parse bằng Zod thật (qua cli-parse.ts); lỗi Zod làm test fail."""
    proc = _run_zod(type_name, payload)
    assert proc.returncode == 0, f"Zod rejected {type_name}: {proc.stderr}"
    return json.loads(proc.stdout)


def zod_accepts(type_name: str, payload: Any) -> bool:
    proc = _run_zod(type_name, payload)
    assert proc.returncode in (0, 1), f"cli-parse crashed: {proc.stderr}"
    return proc.returncode == 0


def schema_validator(type_name: str) -> Draft202012Validator:
    return Draft202012Validator({**SCHEMA, "$ref": f"#/$defs/{type_name}"})


def adapter_for(type_name: str) -> TypeAdapter[Any]:
    return TypeAdapter(getattr(contracts_gen, type_name))


def roundtrip(type_name: str, payload: Any) -> tuple[Any, Any]:
    """Trả (a, b): a = Zod parse fixture, b = JSON sau khi qua JSON Schema + pydantic."""
    a = zod_parse(type_name, payload)
    schema_validator(type_name).validate(a)
    adapter = adapter_for(type_name)
    obj = adapter.validate_python(a)
    # exclude_unset: không bao giờ biến field vắng mặt thành null (Pitfall 5).
    b = adapter.dump_python(obj, mode="json", by_alias=True, exclude_unset=True)
    return a, b


def test_fixtures_collected() -> None:
    assert CASES, "no fixture cases collected"


@pytest.mark.parametrize(
    ("type_name", "case_name", "payload"), CASES, ids=[f"{t}:{n}" for t, n, _ in CASES]
)
def test_roundtrip(type_name: str, case_name: str, payload: Any) -> None:
    a, b = roundtrip(type_name, payload)
    assert zod_parse(type_name, b) == a
    assert b == a

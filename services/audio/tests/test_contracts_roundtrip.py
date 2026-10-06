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


ISSUE_CODES = [
    "STRESS_MISMATCH",
    "EXTRA_PAUSE",
    "FINAL_CONTOUR",
    "FLAT_PITCH",
    "PITCH_DEVIATION",
    "PHONE",
    "WORD_MISSING",
]


@pytest.mark.parametrize("code", ISSUE_CODES)
def test_issue_code_roundtrip(code: str) -> None:
    a, b = roundtrip("IssueCode", code)
    assert a == code
    assert b == code
    assert zod_parse("IssueCode", b) == code


def test_issue_code_rejects_unknown() -> None:
    assert not zod_accepts("IssueCode", "NOT_A_CODE")
    assert not schema_validator("IssueCode").is_valid("NOT_A_CODE")
    with pytest.raises(ValueError):
        adapter_for("IssueCode").validate_python("NOT_A_CODE")


def _fixture(type_name: str, case_name: str) -> Any:
    base = next(p for t, n, p in CASES if t == type_name and n == case_name)
    return json.loads(json.dumps(base))


def test_non_ascii_survives_roundtrip() -> None:
    _, b = roundtrip("ScoreResult", _fixture("ScoreResult", "full"))
    assert b["words"][0]["refPhones"] == "ən"
    assert any(tip["text"] == "Nhấn mạnh *Brown*, không phải *Heat*" for tip in b["tips"])


def test_precision_roundtrip() -> None:
    payload = _fixture("ScoreResult", "full")
    payload["segmentIndex"] = 9007199254740991
    a, b = roundtrip("ScoreResult", payload)
    assert b["segmentIndex"] == 9007199254740991
    assert b["timingMs"]["decode"] == 0.1
    assert b["timingMs"]["f0"] == 1e-9
    assert b["timingMs"]["dtw"] == 12.345678901234567
    assert b == a


def _score_result(**changes: Any) -> Any:
    payload = _fixture("ScoreResult", "full")
    for path, value in changes.items():
        node = payload
        *parents, last = path.split("__")
        for key in parents:
            node = node[int(key) if key.isdigit() else key]
        node[int(last) if last.isdigit() else last] = value
    return payload


def _label(**changes: Any) -> Any:
    return {**_fixture("Label", "flags"), **changes}


def _pydantic_ok(type_name: str, payload: Any) -> bool:
    try:
        adapter_for(type_name).validate_python(payload)
    except ValueError:
        return False
    return True


# (type, payload, expected verdict): Zod, JSON Schema và pydantic phải cho cùng kết luận.
BOUNDARIES = [
    ("ScoreResult", _score_result(scores__overall=0), True),
    ("ScoreResult", _score_result(scores__overall=1), True),
    ("ScoreResult", _score_result(scores__overall=-0.0001), False),
    ("ScoreResult", _score_result(scores__overall=1.0001), False),
    ("ScoreResult", _score_result(issues__1__data__refMs=-1), False),
    ("ScoreResult", _score_result(issues__1__data__refMs=1.5), False),
    ("ScoreResult", _score_result(segmentIndex=9007199254740991), True),
    ("ScoreResult", _score_result(segmentIndex=9007199254740992), False),
    ("ScoreResult", _score_result(attempt=0), False),
    ("Label", _label(overall=1), True),
    ("Label", _label(overall=5), True),
    ("Label", _label(overall=0), False),
    ("Label", _label(overall=6), False),
]


@pytest.mark.parametrize(
    ("type_name", "payload", "valid"),
    BOUNDARIES,
    ids=[f"{i}:{t}:{'ok' if v else 'reject'}" for i, (t, _, v) in enumerate(BOUNDARIES)],
)
def test_python_boundaries(type_name: str, payload: Any, valid: bool) -> None:
    assert _pydantic_ok(type_name, payload) is valid
    assert schema_validator(type_name).is_valid(payload) is valid
    assert zod_accepts(type_name, payload) is valid

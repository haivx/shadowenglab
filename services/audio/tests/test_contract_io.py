"""Test contract_io: một serializer cho mọi contract JSON và ghi file atomic."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import BaseModel, ConfigDict, Field

from audio_service.contract_io import dump_contract, write_contract_json, write_json_atomic


class Demo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ref_ms: Annotated[int, Field(alias="refMs")]
    sound: float | None  # bắt buộc nhưng cho phép null
    ipa: str | None = None  # tuỳ chọn
    text: str | None = None


def test_dump_keeps_null_and_omits_unset_optional() -> None:
    model = Demo(ref_ms=1, sound=None)
    assert dump_contract(model) == {"refMs": 1, "sound": None}


def test_dump_includes_optional_when_set() -> None:
    model = Demo(ref_ms=1, sound=0.5, ipa="ən")
    assert dump_contract(model) == {"refMs": 1, "sound": 0.5, "ipa": "ən"}


def test_dump_uses_json_mode_aliases() -> None:
    assert "refMs" in dump_contract(Demo(ref_ms=2, sound=None))
    assert "ref_ms" not in dump_contract(Demo(ref_ms=2, sound=None))


def test_write_contract_json_round_trips_with_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "lesson.json"
    model = Demo(ref_ms=7, sound=None, ipa="ən", text="Nhấn mạnh")
    write_contract_json(path, model)

    raw = path.read_bytes().decode("utf-8")
    assert raw.endswith("\n")
    assert json.loads(raw) == dump_contract(model)


def test_non_ascii_text_is_not_escaped(tmp_path: Path) -> None:
    path = tmp_path / "lesson.json"
    write_contract_json(path, Demo(ref_ms=1, sound=None, ipa="ən", text="Nhấn mạnh"))
    raw = path.read_text(encoding="utf-8")
    assert "ən" in raw
    assert "Nhấn mạnh" in raw
    assert "\\u" not in raw


def test_parent_directories_are_created(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "c" / "lesson.json"
    write_contract_json(path, Demo(ref_ms=1, sound=None))
    assert json.loads(path.read_text(encoding="utf-8")) == {"refMs": 1, "sound": None}


def test_overwrites_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "lesson.json"
    write_json_atomic(path, {"v": 1})
    write_json_atomic(path, {"v": 2})
    assert json.loads(path.read_text(encoding="utf-8")) == {"v": 2}
    assert [p.name for p in tmp_path.iterdir()] == ["lesson.json"]


def test_failed_replace_keeps_old_content_and_leaves_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "lesson.json"
    write_json_atomic(path, {"v": "old"})
    before = path.read_bytes()

    def boom(src: object, dst: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="replace failed"):
        write_json_atomic(path, {"v": "new"})

    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["lesson.json"]


def test_nan_is_refused_and_previous_file_untouched(tmp_path: Path) -> None:
    path = tmp_path / "lesson.json"
    write_json_atomic(path, {"v": "old"})
    before = path.read_bytes()

    with pytest.raises(ValueError):
        write_json_atomic(path, {"v": float("nan")})
    with pytest.raises(ValueError):
        write_contract_json(path, Demo(ref_ms=1, sound=float("nan")))

    assert path.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["lesson.json"]


def test_nan_is_refused_before_touching_the_filesystem(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "lesson.json"
    with pytest.raises(ValueError):
        write_json_atomic(path, {"v": float("inf")})
    assert not (tmp_path / "missing").exists()


def test_write_json_atomic_writes_mapping(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    write_json_atomic(path, {"a": 1.5})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1.5}
    assert path.read_text(encoding="utf-8").endswith("\n")

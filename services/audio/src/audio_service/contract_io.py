"""Ghi contract JSON (RED stub: chưa hiện thực)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel


def dump_contract(model: BaseModel) -> dict[str, object]:
    return {}


def write_json_atomic(path: Path, data: Mapping[str, object]) -> None:
    return None


def write_contract_json(path: Path, model: BaseModel) -> None:
    return None

"""Ghi contract JSON ra đĩa: một serializer và một writer atomic cho mọi file pipeline sinh ra.

`lesson.json` được poller đọc trong lúc pipeline ghi lại (D-06), nên file không bao giờ được
ở trạng thái ghi dở: ghi vào file tạm cùng thư mục rồi `os.replace`.

Khi dựng model contract, hãy bỏ hẳn field tuỳ chọn thay vì truyền `None`; truyền `None` làm
field đó thành "đã set" và nó sẽ được ghi ra dưới dạng null (`exclude_unset=True`). Field
nullable bắt buộc thì truyền `None` tường minh và vẫn được ghi là null.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel


def dump_contract(model: BaseModel) -> dict[str, object]:
    """Serializer duy nhất cho contract: alias camelCase, giữ null tường minh, bỏ field chưa set."""
    return model.model_dump(mode="json", by_alias=True, exclude_unset=True)


def write_json_atomic(path: Path, data: Mapping[str, object]) -> None:
    """Ghi `data` thành JSON UTF-8 (kết thúc bằng newline) theo kiểu atomic.

    Raise ValueError nếu có NaN/Infinity, trước khi đụng tới hệ thống file. Khi lỗi, file cũ
    giữ nguyên và không còn file tạm.
    """
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)
        raise


def write_contract_json(path: Path, model: BaseModel) -> None:
    write_json_atomic(path, dump_contract(model))

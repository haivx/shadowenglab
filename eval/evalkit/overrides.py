"""Ghi đè ngưỡng trong bộ nhớ để quét (04-03, D-13): không đọc, không ghi file nào.

Các module chấm import ngưỡng THEO TÊN (`from ...thresholds import FLAT_RATIO`), nên đổi
`thresholds.FLAT_RATIO` không làm `rules.engine.FLAT_RATIO` đổi theo. Muốn kết quả của một lần quét
đúng bằng kết quả nếu Liam sửa giá trị trong `thresholds.py`, phải ghi đè trong namespace của MỌI
module có bind tên đó. Khối `override_thresholds` khôi phục mọi giá trị trong `finally`, kể cả khi
có ngoại lệ (T-04-07).

`CONSUMER_MODULES` phải liệt kê mọi module import hằng ngưỡng; test quét mã nguồn để bắt trường hợp
thêm module mà quên danh sách này.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType

THRESHOLDS_MODULE = "audio_service.scoring.thresholds"

CONSUMER_MODULES = (
    THRESHOLDS_MODULE,
    "audio_service.scoring.align",
    "audio_service.scoring.metrics",
    "audio_service.scoring.prominence",
    "audio_service.rules.engine",
)


def _is_threshold_name(name: str) -> bool:
    return name.isupper() and name.isidentifier()


def bound_in(name: str) -> list[str]:
    """Module (theo thứ tự `CONSUMER_MODULES`) có thuộc tính tên `name`."""
    return [
        module_name
        for module_name in CONSUMER_MODULES
        if hasattr(importlib.import_module(module_name), name)
    ]


@contextmanager
def override_thresholds(**values: float) -> Iterator[None]:
    """Đặt `values` lên mọi module có bind tên đó; ra khỏi khối thì khôi phục giá trị cũ.

    Tên không phải hằng trong `audio_service.scoring.thresholds` -> `KeyError` TRƯỚC khi đổi gì.
    """
    thresholds = importlib.import_module(THRESHOLDS_MODULE)
    unknown = [
        name for name in values if not (_is_threshold_name(name) and hasattr(thresholds, name))
    ]
    if unknown:
        raise KeyError(", ".join(unknown))

    saved: list[tuple[ModuleType, str, object]] = []
    try:
        for name, value in values.items():
            for module_name in CONSUMER_MODULES:
                module = importlib.import_module(module_name)
                if hasattr(module, name):
                    saved.append((module, name, getattr(module, name)))
                    setattr(module, name, value)
        yield
    finally:
        for module, name, old in reversed(saved):
            setattr(module, name, old)

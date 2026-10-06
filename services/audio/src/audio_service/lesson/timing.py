"""Đo thời gian từng bước của pipeline tạo bài (FND-07) và in bảng thời gian.

`StepTimer.step(name)` CỘNG DỒN thời gian theo tên, vì F0/PPG chạy lặp cho từng segment.
Không lồng các bước vào nhau, nếu không `total()` đếm hai lần.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager


class StepTimer:
    def __init__(self) -> None:
        self._raw: dict[str, float] = {}

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self._raw[name] = self._raw.get(name, 0.0) + (time.perf_counter() - t0)

    @property
    def timings(self) -> dict[str, float]:
        """Giây theo bước, làm tròn 0.01, theo thứ tự bước xuất hiện lần đầu."""
        return {name: round(sec, 2) for name, sec in self._raw.items()}

    def total(self) -> float:
        return round(sum(self._raw.values()), 2)


def format_timing_table(timings: Mapping[str, float], extras: Mapping[str, str]) -> str:
    """Bảng cột cố định: mỗi bước một dòng, dòng `total`, rồi các dòng thông tin phụ."""
    width = max([len("total"), *(len(name) for name in timings)])
    lines = [f"{'step':<{width}}  {'seconds':>9}", f"{'-' * width}  {'-' * 9}"]
    for name, sec in timings.items():
        lines.append(f"{name:<{width}}  {sec:>9.2f}")
    lines.append(f"{'-' * width}  {'-' * 9}")
    lines.append(f"{'total':<{width}}  {round(sum(timings.values()), 2):>9.2f}")
    if extras:
        lines.append("")
        key_width = max(len(key) for key in extras)
        lines.extend(f"{key:<{key_width}}  {value}" for key, value in extras.items())
    return "\n".join(lines)

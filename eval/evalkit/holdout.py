"""Log mở held-out, digest nhãn và kiểm đóng băng (04-06, EVL-03, D-09, D-12, D-16).

Mỗi lần `analyze.py --holdout` chấm xong (mã 0 hoặc 1) thêm đúng một dòng vào
`eval/holdout_log.jsonl` (append-only, được commit). Dòng đầu là mốc đóng băng: từ lần mở thứ hai,
nhãn held-out không được đổi so với `digests` của dòng đầu (`check_frozen`). Khoá JSON là camelCase
như 04-01 mục E2.

Chỉ I/O file nhỏ và băm; `make_entry` đọc version từ scorer, không chấm gì.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from audio_service.config import REPO_ROOT
from audio_service.contracts_gen import EvalCase

HOLDOUT_LOG_PATH = REPO_ROOT / "eval" / "holdout_log.jsonl"
HELDOUT = "heldout"


class HoldoutLogError(Exception):
    """Log mở held-out hỏng (dòng không phải JSON hay thiếu khoá); thoát 2."""


@dataclass(frozen=True)
class HoldoutEntry:
    """Một lần mở held-out: lúc nào, bản nào, và nhãn lúc đó (04-01 mục E2)."""

    opened_at: str
    thresholds_version: str
    scorer_version: str
    feat_version: str
    git_sha: str
    splits: dict[str, str]
    digests: dict[str, str]

    def to_json(self) -> dict[str, Any]:
        return {
            "openedAt": self.opened_at,
            "thresholdsVersion": self.thresholds_version,
            "scorerVersion": self.scorer_version,
            "featVersion": self.feat_version,
            "gitSha": self.git_sha,
            "splits": dict(self.splits),
            "digests": dict(self.digests),
        }

    @classmethod
    def from_json(cls, payload: Any) -> HoldoutEntry:
        """Dựng từ một dict đã parse; thiếu khoá hoặc sai kiểu -> HoldoutLogError."""
        try:
            entry = cls(
                opened_at=_text(payload["openedAt"]),
                thresholds_version=_text(payload["thresholdsVersion"]),
                scorer_version=_text(payload["scorerVersion"]),
                feat_version=_text(payload["featVersion"]),
                git_sha=_text(payload["gitSha"]),
                splits=_text_map(payload["splits"]),
                digests=_text_map(payload["digests"]),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise HoldoutLogError(f"thiếu hoặc sai khoá ({type(exc).__name__})") from None
        return entry


def _text(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("không phải chuỗi")
    return value


def _text_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError("không phải object")
    return {_text(key): _text(item) for key, item in value.items()}


def case_digest(case: EvalCase) -> str:
    """sha256 của JSON chuẩn hoá của case (camelCase, bỏ trường vắng, khoá sắp, không khoảng trắng).

    Mọi trường nhãn đều vào digest: errorType, wordIndex, alsoPresent, split, clip, note, dấu nhận
    diện câu (D-09: sửa bất kỳ trường nào sau lần mở đầu đều bị phát hiện).
    """
    payload = case.model_dump(mode="json", by_alias=True, exclude_none=True)
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_entry(cases: Sequence[EvalCase], *, opened_at: str, git_sha: str) -> HoldoutEntry:
    """Dòng log cho lần mở này: split của mọi case, digest của case held-out, version hiện tại."""
    from audio_service.scoring.features import FEAT_VERSION
    from audio_service.scoring.thresholds import SCORER_VERSION, THRESHOLDS_VERSION

    return HoldoutEntry(
        opened_at=opened_at,
        thresholds_version=THRESHOLDS_VERSION,
        scorer_version=SCORER_VERSION,
        feat_version=FEAT_VERSION,
        git_sha=git_sha,
        splits={case.case_id: str(case.split) for case in cases},
        digests={case.case_id: case_digest(case) for case in cases if case.split == HELDOUT},
    )


def read_log(path: Path) -> list[HoldoutEntry]:
    """Mọi dòng của log theo thứ tự; thiếu file -> []. Dòng hỏng -> HoldoutLogError nêu số dòng."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as exc:
        raise HoldoutLogError(f"không đọc được {path.name} ({type(exc).__name__})") from None
    entries: list[HoldoutEntry] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entries.append(HoldoutEntry.from_json(json.loads(line)))
        except (ValueError, HoldoutLogError):
            raise HoldoutLogError(
                f"{path.name} dòng {number}: không phải một dòng log hợp lệ"
            ) from None
    return entries


def count_openings(path: Path) -> int:
    """Số dòng không trống của log (không parse); thiếu file hoặc không đọc được -> 0."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def is_opened(path: Path) -> bool:
    """Held-out đã từng được mở (log có ít nhất một dòng). Log hỏng -> HoldoutLogError."""
    return bool(read_log(path))


def append_entry(path: Path, entry: HoldoutEntry) -> None:
    """Thêm một dòng vào cuối log atomic: cũ + mới -> `.part` -> `os.replace` (T-04-16)."""
    old = ""
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old and not old.endswith("\n"):
            old += "\n"
    line = json.dumps(entry.to_json(), ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        part.write_text(old + line + "\n", encoding="utf-8")
        os.replace(part, path)
    finally:
        part.unlink(missing_ok=True)

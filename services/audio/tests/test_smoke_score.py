"""Phán quyết và lần chạy đầu-cuối của scripts/smoke_score.py (03-11, PRO-03, PRO-04).

`verdict` là hàm thuần. Lần chạy đầu-cuối dùng một bài `ready` tổng hợp (hai câu giả giọng trong một
stem, ffmpeg thật) trên DATA_DIR tạm và chứng minh script CHỈ ĐỌC: cây thư mục không đổi một byte.
Bài thật là `make smoke-score`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import soundfile as sf
from synth import DEFAULT_WORDS, SynthWord, synth_sentence

from audio_service.config import REPO_ROOT, get_settings

LESSON_ID = "01HZX3Y7Q8K2M4N6P8R0S2T4V6"
VIDEO_ID = "dUDi-F6eAvk"
SR = 16000

# Câu khác hẳn DEFAULT_WORDS (formant, độ dài, cuối câu đi lên): căn kém ở cả hai chiều.
OTHER_WORDS = (
    SynthWord("one", 0.26, 190, 175, (350, 2500)),
    SynthWord("two", 0.34, 170, 200, (900, 1300)),
    SynthWord("three", 0.24, 205, 195, (450, 950)),
    SynthWord("four", 0.30, 180, 190, (650, 2000)),
    SynthWord("five", 0.28, 185, 215, (300, 1800)),
    SynthWord("six", 0.30, 190, 250, (500, 1100)),
)


def _load_smoke_module() -> ModuleType:
    path = Path(REPO_ROOT) / "scripts" / "smoke_score.py"
    spec = importlib.util.spec_from_file_location("smoke_score_for_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def smoke() -> Iterator[ModuleType]:
    module = _load_smoke_module()
    yield module
    sys.modules.pop("smoke_score_for_test", None)


# --- verdict (hàm thuần) -----------------------------------------------------------------------


def _self_rows(smoke: ModuleType, **overrides: float) -> list:
    rows = []
    for index in range(5):
        values = {"overall": 0.995, "issues": 0, "ms": 400.0}
        values.update(overrides)
        rows.append(smoke.SelfRow(index=index, text=f"câu {index}", **values))
    return rows


def _cross_rows(smoke: ModuleType, overall: float = 0.5, align_ok: bool = False) -> list:
    return [
        smoke.CrossRow(index=i, other=(i + 1) % 5, overall=overall, align_ok=align_ok)
        for i in range(5)
    ]


def test_good_run_is_score_ok(smoke: ModuleType) -> None:
    assert smoke.verdict(_self_rows(smoke), _cross_rows(smoke)) == ("SCORE OK", 0)


def test_a_self_compare_issue_fails_and_names_the_sentence(smoke: ModuleType) -> None:
    rows = _self_rows(smoke)
    rows[2] = rows[2]._replace(issues=1)

    message, code = smoke.verdict(rows, _cross_rows(smoke))

    assert code == 1
    assert message.startswith("SCORE FAILED:")
    assert "câu 2" in message or "#2" in message


def test_low_self_median_fails(smoke: ModuleType) -> None:
    message, code = smoke.verdict(_self_rows(smoke, overall=0.95), _cross_rows(smoke))

    assert code == 1
    assert "trung vị" in message


def test_one_self_compare_below_the_floor_fails_even_with_a_good_median(smoke: ModuleType) -> None:
    rows = _self_rows(smoke)
    rows[1] = rows[1]._replace(overall=0.85)

    message, code = smoke.verdict(rows, _cross_rows(smoke))

    assert code == 1
    assert "0.85" in message


def test_slow_p95_fails(smoke: ModuleType) -> None:
    message, code = smoke.verdict(_self_rows(smoke, ms=3200.0), _cross_rows(smoke))

    assert code == 1
    assert "p95" in message


def test_p95_at_the_limit_fails_and_just_under_passes(smoke: ModuleType) -> None:
    assert smoke.verdict(_self_rows(smoke, ms=3000.0), _cross_rows(smoke))[1] == 1
    assert smoke.verdict(_self_rows(smoke, ms=2999.0), _cross_rows(smoke))[1] == 0


def test_high_cross_median_fails_criterion_d_a(smoke: ModuleType) -> None:
    message, code = smoke.verdict(_self_rows(smoke), _cross_rows(smoke, overall=0.65))

    assert code == 1
    assert "chéo" in message


def test_a_cross_pair_with_alignment_ok_fails_criterion_d_a(smoke: ModuleType) -> None:
    cross = _cross_rows(smoke)
    cross[3] = cross[3]._replace(align_ok=True)

    message, code = smoke.verdict(_self_rows(smoke), cross)

    assert code == 1
    assert "căn" in message


def test_reasons_are_joined_when_several_checks_fail(smoke: ModuleType) -> None:
    message, code = smoke.verdict(
        _self_rows(smoke, overall=0.95, ms=3200.0), _cross_rows(smoke, overall=0.7)
    )

    assert code == 1
    assert "trung vị" in message and "p95" in message and "chéo" in message


def test_empty_input_is_a_failure_not_a_pass(smoke: ModuleType) -> None:
    assert smoke.verdict([], [])[1] == 1


# --- đầu-cuối trên bài tổng hợp ----------------------------------------------------------------


def _synthetic_stem() -> tuple[np.ndarray, list[list[tuple[str, float, float]]]]:
    first, first_marks = synth_sentence(DEFAULT_WORDS, dur_scale=1.5, seed=1)
    second, second_marks = synth_sentence(OTHER_WORDS, dur_scale=1.8, seed=2)
    offset = len(first) / SR
    shifted = [(t, s + offset, e + offset) for t, s, e in second_marks]
    return np.concatenate([first, second]), [first_marks, shifted]


def _write_lesson(root: Path, *, status: str = "ready") -> None:
    audio, sentences = _synthetic_stem()
    total = len(audio) / SR
    segments = [
        {
            "index": i,
            "text": f"Sentence {i}",
            "start": marks[0][1],
            "end": marks[-1][2],
            "endExtraMs": 0,
            "words": [
                {"i": w, "text": text, "start": start, "end": end, "asrProb": 0.95}
                for w, (text, start, end) in enumerate(marks)
            ],
        }
        for i, marks in enumerate(sentences)
    ]
    lesson = {
        "id": LESSON_ID,
        "videoId": VIDEO_ID,
        "title": "Synthetic",
        "durationSec": total,
        "range": {"start": 0.0, "end": total},
        "padMs": 150,
        "status": status,
        "segments": segments if status == "ready" else [],
        "createdAt": "2026-10-07T08:00:00.000Z",
    }
    lesson_json = root / "lessons" / LESSON_ID / "lesson.json"
    lesson_json.parent.mkdir(parents=True)
    lesson_json.write_text(json.dumps(lesson), encoding="utf-8")
    stems = root / "videos" / VIDEO_ID / "stems" / f"0-{round(total * 1000)}"
    stems.mkdir(parents=True)
    sf.write(stems / "vocals.wav", audio, SR, subtype="FLOAT", format="WAV")


def _listing(root: Path) -> list[tuple[str, int, int]]:
    """Mọi file và thư mục dưới `root`: (đường dẫn tương đối, kích thước, mtime ns)."""
    entries = []
    for path in sorted(root.rglob("*")):
        stat = path.stat()
        size = stat.st_size if path.is_file() else -1
        entries.append((str(path.relative_to(root)), size, stat.st_mtime_ns))
    return entries


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "data"
    root.mkdir()
    # setenv trước để monkeypatch khôi phục cả những gì main() tự đặt.
    monkeypatch.setenv("DATA_DIR", str(root))
    monkeypatch.setenv("SHADOWENGLAB_CONFIG_DIR", str(tmp_path / "config"))
    get_settings.cache_clear()
    yield root.resolve()
    get_settings.cache_clear()


def _leftover_temp_dirs() -> set[str]:
    return {p.name for p in Path(tempfile.gettempdir()).glob("shadowenglab-smoke-score-*")}


def test_synthetic_lesson_passes_prints_a_line_per_sentence_and_touches_nothing(
    smoke: ModuleType, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_lesson(data_dir)
    before = _listing(data_dir)
    temp_before = _leftover_temp_dirs()

    code = smoke.main(["--data-dir", str(data_dir)])

    out = capsys.readouterr().out
    assert code == 0, out
    assert out.strip().splitlines()[-1] == "SCORE OK"
    assert LESSON_ID in out
    for index in (0, 1):
        assert any(line.lstrip().startswith(str(index)) for line in out.splitlines()), out
    assert _listing(data_dir) == before, "smoke-score chỉ được đọc DATA_DIR (T-03-22)"
    assert not (data_dir / "app.db").exists()
    assert not (data_dir / "tmp").exists()
    assert _leftover_temp_dirs() == temp_before, "thư mục tạm phải bị xoá trong finally"


def test_failing_run_exits_one_with_the_reason_on_the_last_line(
    smoke: ModuleType,
    data_dir: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_lesson(data_dir)
    monkeypatch.setattr(smoke, "P95_MAX_MS", 0.001)  # không máy nào chấm trong 1 µs

    code = smoke.main(["--data-dir", str(data_dir)])

    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert code == 1
    assert last.startswith("SCORE FAILED:") and "p95" in last


def test_no_ready_lesson_exits_two_with_a_clear_message(
    smoke: ModuleType, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = smoke.main(["--data-dir", str(data_dir)])

    assert code == 2
    assert "ready" in capsys.readouterr().err


def test_a_lesson_that_is_not_ready_is_not_picked(
    smoke: ModuleType, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_lesson(data_dir, status="separating")

    code = smoke.main(["--data-dir", str(data_dir)])

    assert code == 2
    assert "ready" in capsys.readouterr().err


def test_unknown_lesson_id_exits_two(
    smoke: ModuleType, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_lesson(data_dir)

    code = smoke.main(["--data-dir", str(data_dir), "--lesson", "01HZX3Y7Q8K2M4N6P8R0S2T4V7"])

    assert code == 2
    assert capsys.readouterr().err.strip() != ""


def test_a_lesson_with_fewer_than_two_usable_sentences_exits_two(
    smoke: ModuleType, data_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_lesson(data_dir)

    code = smoke.main(["--data-dir", str(data_dir), "--limit", "1"])

    assert code == 2
    assert "2" in capsys.readouterr().err


def test_a_missing_data_dir_exits_two(
    smoke: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = smoke.main(["--data-dir", str(tmp_path / "nowhere")])

    assert code == 2
    assert capsys.readouterr().err.strip() != ""

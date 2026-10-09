"""Smoke chấm ngữ điệu trên một bài thật: tự so, chéo câu và thời gian (Phase 3, PRO-03, PRO-04).

    uv run --project services/audio --frozen python scripts/smoke_score.py \
        [--lesson ID] [--limit 20] [--data-dir PATH]

Chọn bài `ready` mới tạo nhất (hoặc `--lesson`) trong DATA_DIR, lấy tối đa `--limit` câu dài 3-8 s
(rải đều trong bài). Với mỗi câu, "người học" là chính lát vocal của bản gốc, được mã hoá webm/opus
bằng ffmpeg rồi chuẩn hoá y như một lượt tải lên (`normalize_to_wav16k`, VAD), tính feature và chấm
so với bản gốc của câu đó (tự so, mong đợi gần 100 %). Cặp chéo là bản ghi của câu i chấm với bản
gốc của câu (i + 1) mod N (mong đợi thấp và căn kém, tiêu chí D-a của 03-01 mục D).

In một bảng cố định cộng các dòng tóm tắt, rồi `SCORE OK` (thoát 0) hoặc `SCORE FAILED: <lý do>`
(thoát 1). Thoát 2: tham số sai, không có bài `ready`, thiếu audio bản gốc hoặc dưới 2 câu dùng
được.

CHỈ ĐỌC DATA_DIR (T-03-22): `ref_prosody_for_segment(..., write_cache=False)` không ghi sidecar,
không đụng SQLite, file tạm nằm trong thư mục tạm của hệ thống và bị xoá trong `finally`. Thời gian
mỗi câu = chuẩn hoá + VAD + feature người học + chấm (không tính mã hoá webm, việc của trình duyệt;
không tính feature bản gốc vì lượt thật đọc từ sidecar). Script chỉ in số, không ghi gì vào repo.
"""

from __future__ import annotations

import argparse
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
import soundfile as sf

MIN_SENTENCE_S = 3.0
MAX_SENTENCE_S = 8.0
SELF_MEDIAN_MIN = 0.97  # tự so qua opus: "gần 100 %" kiểm bằng trung vị >= 0.97 ...
SELF_MIN = 0.90  # ... không câu nào dưới 0.90 và không có issue nào
P95_MAX_MS = 3000.0  # PRO-04: chấm một lượt < 3 s
CROSS_MEDIAN_MAX = 0.6  # 03-01 mục D-a: trung vị chéo câu < 0.6 và mọi cặp căn không ok
MIN_SENTENCES = 2
TEXT_WIDTH = 38
TABLE_HEADER = "   #  dài(s)  tự so  issue      ms  chéo vs  chéo  căn  câu"


class SelfRow(NamedTuple):
    """Một câu tự so: điểm tổng, số issue và thời gian chấm (ms)."""

    index: int
    text: str
    overall: float
    issues: int
    ms: float


class CrossRow(NamedTuple):
    """Bản ghi của câu `index` chấm với bản gốc của câu `other`."""

    index: int
    other: int
    overall: float
    align_ok: bool


def verdict(rows: Sequence[SelfRow], cross: Sequence[CrossRow]) -> tuple[str, int]:
    """(`SCORE OK`, 0) hoặc (`SCORE FAILED: <lý do>`, 1). Hàm thuần, đọc ngưỡng ở module."""
    if not rows:
        return "SCORE FAILED: không có câu nào được chấm", 1
    problems: list[str] = []

    median = statistics.median(row.overall for row in rows)
    if median < SELF_MEDIAN_MIN:
        problems.append(f"trung vị tự so {median:.3f} < {SELF_MEDIAN_MIN}")
    for row in rows:
        if row.overall < SELF_MIN:
            problems.append(f"câu #{row.index} tự so {row.overall:.2f} < {SELF_MIN}")
        if row.issues > 0:
            problems.append(f"câu #{row.index} tự so có {row.issues} issue")

    p95 = float(np.percentile([row.ms for row in rows], 95))
    if p95 >= P95_MAX_MS:
        problems.append(f"p95 thời gian chấm {p95:.0f} ms >= {P95_MAX_MS:.0f} ms")

    if not cross:
        problems.append("không có cặp chéo câu nào để kiểm tiêu chí D-a")
    else:
        cross_median = statistics.median(pair.overall for pair in cross)
        if cross_median >= CROSS_MEDIAN_MAX:
            problems.append(f"trung vị chéo câu {cross_median:.3f} >= {CROSS_MEDIAN_MAX}")
        aligned = [f"#{pair.index}->#{pair.other}" for pair in cross if pair.align_ok]
        if aligned:
            problems.append("cặp chéo câu có căn ok: " + ", ".join(aligned))

    if problems:
        return "SCORE FAILED: " + "; ".join(problems), 1
    return "SCORE OK", 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chấm tự so + chéo câu trên một bài thật, chỉ đọc DATA_DIR."
    )
    parser.add_argument("--lesson", help="id bài (mặc định: bài ready mới tạo nhất)")
    parser.add_argument("--limit", type=int, default=20, help="số câu tối đa, mặc định 20")
    parser.add_argument("--data-dir", type=Path, help="DATA_DIR (mặc định: theo cấu hình app)")
    return parser.parse_args(argv)


def _usage_error(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _failed(reason: str) -> int:
    print(f"SCORE FAILED: {reason}")
    return 1


def _pick_evenly(candidates: list[int], limit: int) -> list[int]:
    """Tối đa `limit` phần tử rải đều (xác định), giữ thứ tự."""
    if limit <= 0:
        return []
    if len(candidates) <= limit:
        return candidates
    return [candidates[(k * len(candidates)) // limit] for k in range(limit)]


def _encode_like_a_browser(clip: np.ndarray, workdir: Path, name: str) -> Path:
    """Mảng 16 kHz mono -> webm/opus bằng ffmpeg (giả lập bản ghi MediaRecorder của Chrome)."""
    wav = workdir / f"{name}.src.wav"
    out = workdir / f"{name}.webm"
    sf.write(wav, clip, 16000, subtype="PCM_16", format="WAV")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "libopus", out],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60.0,
    )
    return out


def _normalize_like_an_upload(src: Path, workdir: Path, name: str) -> np.ndarray:
    """Đúng các bước của `routers/attempts._normalize`: sniff -> ffmpeg 16 kHz mono -> mảng."""
    from audio_service.lesson import audio_io, normalize

    demuxer = normalize.sniff_demuxer(src.read_bytes()[:16])
    if demuxer is None:
        raise ValueError("ffmpeg không tạo ra webm")
    wav = workdir / f"{name}.norm.wav"
    normalize.normalize_to_wav16k(src, wav, demuxer)
    audio, sr = audio_io.read_audio(wav)
    return audio_io.to_mono_16k(audio, sr)


def _format_table(
    rows: Sequence[SelfRow], cross: Sequence[CrossRow], durations: dict[int, float]
) -> str:
    by_index = {pair.index: pair for pair in cross}
    lines = [TABLE_HEADER]
    for row in rows:
        pair = by_index.get(row.index)
        if pair is None:
            cross_text = f"{'-':>7}  {'-':>4}  {'-':>3}"
        else:
            quality = "ok" if pair.align_ok else "kém"
            cross_text = f"{'#' + str(pair.other):>7}  {pair.overall:4.2f}  {quality:>3}"
        lines.append(
            f"{row.index:4d}  {durations[row.index]:6.1f}  {row.overall:5.3f}  {row.issues:5d}"
            f"  {row.ms:6.0f}  {cross_text}  {row.text[:TEXT_WIDTH]}"
        )
    return "\n".join(lines)


def _summary(rows: Sequence[SelfRow], cross: Sequence[CrossRow]) -> list[str]:
    overalls = [row.overall for row in rows]
    times = [row.ms for row in rows]
    lines = [
        f"tự so: trung vị {statistics.median(overalls):.3f}, nhỏ nhất {min(overalls):.3f}, "
        f"tổng issue {sum(row.issues for row in rows)} ({len(rows)} câu)",
        "thời gian chấm (chuẩn hoá + VAD + feature người học + chấm): "
        f"p50 {np.percentile(times, 50):.0f} ms, p95 {np.percentile(times, 95):.0f} ms, "
        f"lớn nhất {max(times):.0f} ms",
    ]
    if cross:
        bad = sum(1 for pair in cross if not pair.align_ok)
        lines.append(
            f"chéo câu: trung vị {statistics.median(pair.overall for pair in cross):.3f}, "
            f"căn không ok {bad}/{len(cross)} cặp"
        )
    else:
        lines.append("chéo câu: không có cặp nào")
    return lines


def _choose_lesson(lesson_id: str | None) -> Any:
    """Bài cần chấm (`Lesson`), hoặc một chuỗi thông báo lỗi (thoát 2)."""
    from audio_service.config import InvalidIdError
    from audio_service.lesson import store

    if lesson_id is not None:
        try:
            lesson = store.load_lesson(lesson_id)
        except (InvalidIdError, OSError, ValueError):
            return f"không đọc được bài {lesson_id} trong DATA_DIR"
        if lesson.status != "ready":
            return f"bài {lesson_id} chưa ở trạng thái ready (đang {lesson.status})"
        return lesson
    ready = [lesson for lesson in store.iter_lessons() if lesson.status == "ready"]
    if not ready:
        return "DATA_DIR không có bài nào ở trạng thái ready"
    return max(ready, key=lambda lesson: lesson.created_at)


def _run(args: argparse.Namespace, root: Path) -> int:
    if args.data_dir is not None:
        if not args.data_dir.is_dir():
            return _usage_error(f"--data-dir không phải thư mục: {args.data_dir}")
        os.environ["DATA_DIR"] = str(args.data_dir)
        # settings.json của app có thể ghi đè DATA_DIR; trỏ cấu hình vào chỗ trống để --data-dir
        # thắng.
        os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")

    # Import sau khi đặt biến môi trường: get_settings() phân giải DATA_DIR một lần.
    from audio_service import config
    from audio_service.lesson import audio_io, features, pipeline, vad
    from audio_service.scoring import ref_cache
    from audio_service.scoring.features import prepare_features
    from audio_service.scoring.scorer import score_prosody

    config.get_settings.cache_clear()
    data_root = config.data_root()
    if not data_root.is_dir():
        return _usage_error(f"DATA_DIR không tồn tại: {data_root}")
    if root.resolve().is_relative_to(data_root):
        return _usage_error("thư mục tạm nằm trong DATA_DIR; đặt TMPDIR ra ngoài rồi chạy lại")

    lesson = _choose_lesson(args.lesson)
    if isinstance(lesson, str):
        return _usage_error(lesson)

    candidates = [
        seg.index
        for seg in lesson.segments
        if MIN_SENTENCE_S <= seg.end - seg.start <= MAX_SENTENCE_S
    ]
    selected = _pick_evenly(candidates, args.limit)
    if len(selected) < MIN_SENTENCES:
        return _usage_error(
            f"cần ít nhất {MIN_SENTENCES} câu dài {MIN_SENTENCE_S:.0f}-{MAX_SENTENCE_S:.0f} s "
            f"(bài có {len(candidates)} câu như vậy, --limit {args.limit})"
        )

    try:
        vocals16, base = pipeline.load_range_vocals16(lesson)
        refs = {i: pipeline.ref_prosody_for_segment(lesson, i, write_cache=False) for i in selected}
    except pipeline.StepError as exc:  # gồm RefAudioMissing
        return _usage_error(exc.message)
    stop = pipeline._stem_span(lesson)[3]  # cùng cửa sổ mà ref_prosody_for_segment dùng

    print(f"LESSON_ID={lesson.id} video={lesson.video_id} DATA_DIR={data_root}")
    print(
        f"{len(selected)} câu dài {MIN_SENTENCE_S:.0f}-{MAX_SENTENCE_S:.0f} s "
        f"(bài có {len(lesson.segments)} câu)"
    )

    rows: list[SelfRow] = []
    learner = {}
    durations: dict[int, float] = {}
    for i in selected:
        seg = lesson.segments[i]
        durations[i] = seg.end - seg.start
        window = ref_cache.read_feature_window(lesson.id, i) or features.segment_window(
            seg.start, seg.end, lesson.pad_ms, seg.end_extra_ms, lo=base, hi=stop
        )
        clip = audio_io.slice_seconds(
            vocals16, audio_io.TARGET_SR, window[0] - base, window[1] - base
        )
        name = f"s{i:04d}"
        try:
            src = _encode_like_a_browser(clip, root, name)
        except (subprocess.SubprocessError, OSError, sf.LibsndfileError) as exc:
            return _failed(f"không mã hoá được câu #{i} ({type(exc).__name__})")

        started = time.perf_counter()
        try:
            mono = _normalize_like_an_upload(src, root, name)
        except (subprocess.SubprocessError, OSError, ValueError, sf.LibsndfileError) as exc:
            return _failed(f"không chuẩn hoá được câu #{i} ({type(exc).__name__})")
        if not vad.is_voiced(mono):
            # Lượt thật sẽ bị từ chối no_speech: coi là hỏng, không tạo cặp chéo cho câu này.
            rows.append(SelfRow(i, seg.text, 0.0, 0, (time.perf_counter() - started) * 1000.0))
            continue
        user = prepare_features(mono)
        score = score_prosody(refs[i].features, user, refs[i].words)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        rows.append(SelfRow(i, seg.text, score.overall, len(score.issues), elapsed_ms))
        learner[i] = user

    cross: list[CrossRow] = []
    for position, i in enumerate(selected):
        if i not in learner:
            continue
        other = selected[(position + 1) % len(selected)]
        pair = score_prosody(refs[other].features, learner[i], refs[other].words)
        cross.append(CrossRow(i, other, pair.overall, pair.alignment.ok))

    print(_format_table(rows, cross, durations))
    print()
    for line in _summary(rows, cross):
        print(line)
    message, code = verdict(rows, cross)
    print(message)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="shadowenglab-smoke-score-"))
    try:
        return _run(args, root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(code)

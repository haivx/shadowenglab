"""Smoke test job runner qua API thật: hai bài tạo liên tiếp, không có OPENAI_API_KEY (Phase 2).

    uv run --project services/audio --frozen python scripts/smoke_jobs.py <url> \
        [--range-a 0:150] [--range-b 150:300] [--timeout-s 900]

Chạy API thật trong process (uvicorn.Server trong một thread, 127.0.0.1, cổng trống) trên một
DATA_DIR/cấu hình/.env tạm, bỏ OPENAI_API_KEY khỏi môi trường, POST hai bài liên tiếp qua HTTP rồi
poll mỗi 0,5 s. In bảng trạng thái theo thời gian và `JOBS OK` (thoát 0) chỉ khi cả bốn điều đúng:

1. bài 2 rời `queued` sang `downloading` trước khi bài 1 `ready`;
2. hai bài không bao giờ cùng ở một bước model (separating/transcribing/segmenting/analyzing);
3. GET /lessons trả lời < 1 s ở mọi vòng poll;
4. cả hai bài kết thúc `ready`.

Ngược lại in `JOBS FAILED: <lý do>` và thoát 1. Thoát 2: tham số sai. Thư mục tạm luôn bị xoá khi
thoát; không đụng tới dữ liệu hay cấu hình thật của người dùng (T-02-51).
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

POLL_INTERVAL_S = 0.5
LIST_LATENCY_LIMIT_S = 1.0
HEALTH_TIMEOUT_S = 120.0
MODEL_STEPS = frozenset({"separating", "transcribing", "segmenting", "analyzing"})

# (giây từ lúc POST bài 1, trạng thái bài 1, trạng thái bài 2, độ trễ GET /lessons tính bằng giây)
Sample = tuple[float, str, str, float]


def check_timeline(samples: Sequence[Sample]) -> list[str]:
    """Lý do thất bại theo đúng bốn điều kiện của `JOBS OK`; danh sách rỗng là đạt. Hàm thuần."""
    problems: list[str] = []
    if not samples:
        return ["không có mẫu poll nào"]

    if not any(b == "downloading" and a != "ready" for _, a, b, _ in samples):
        problems.append(
            "bài 2 không sang downloading trước khi bài 1 ready (hai bài bị xếp hàng nối)"
        )

    overlap = next((s for s in samples if s[1] in MODEL_STEPS and s[2] in MODEL_STEPS), None)
    if overlap is not None:
        problems.append(
            f"hai bài cùng ở bước model lúc t={overlap[0]:.1f}s ({overlap[1]} và {overlap[2]})"
        )

    slowest = max(latency for _, _, _, latency in samples)
    if slowest >= LIST_LATENCY_LIMIT_S:
        problems.append(f"GET /lessons chậm {slowest:.2f}s (giới hạn {LIST_LATENCY_LIMIT_S:.0f}s)")

    _, last_a, last_b, _ = samples[-1]
    if last_a != "ready" or last_b != "ready":
        problems.append(f"trạng thái cuối là {last_a} và {last_b}, cần cả hai ready")
    return problems


def format_timeline(samples: Sequence[Sample]) -> str:
    """Bảng gọn: mỗi dòng là một lần đổi trạng thái, kèm GET /lessons chậm nhất từ dòng trước."""
    rows = ["  t (s)  bài 1          bài 2          GET /lessons max (ms)"]
    previous: tuple[str, str] | None = None
    window_max = 0.0
    for t, a, b, latency in samples:
        window_max = max(window_max, latency)
        if (a, b) != previous:
            rows.append(f"  {t:6.1f}  {a:<13}  {b:<13}  {window_max * 1000:6.0f}")
            previous = (a, b)
            window_max = 0.0
    return "\n".join(rows)


def _parse_range(text: str) -> tuple[float, float]:
    try:
        start_text, end_text = text.split(":")
        start, end = float(start_text), float(end_text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"khoảng phải có dạng START:END, nhận '{text}'") from None
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError(f"khoảng không hợp lệ: '{text}'")
    return start, end


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tạo hai bài liên tiếp qua API thật, không key, kiểm tra chúng không chặn nhau."
    )
    parser.add_argument("url", help="link video YouTube")
    parser.add_argument("--range-a", type=_parse_range, default=(0.0, 150.0), help="mặc định 0:150")
    parser.add_argument(
        "--range-b", type=_parse_range, default=(150.0, 300.0), help="mặc định 150:300"
    )
    parser.add_argument("--timeout-s", type=float, default=900.0, help="mặc định 900")
    return parser.parse_args(argv)


def _isolate_environment(root: Path) -> None:
    """Trỏ dữ liệu/cấu hình/.env vào thư mục tạm TRƯỚC khi import audio_service (T-02-51)."""
    data_dir = root / "data"
    data_dir.mkdir()
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["SHADOWENGLAB_CONFIG_DIR"] = str(root / "config")
    os.environ["SHADOWENGLAB_ENV_FILE"] = str(root / "env" / ".env")
    os.environ.pop("OPENAI_API_KEY", None)  # chứng minh tiêu chí 4: chạy được khi thiếu key


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(client: httpx.Client, deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            if client.get("/health").status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    return False


def _create(client: httpx.Client, url: str, span: tuple[float, float]) -> str:
    response = client.post("/lessons", json={"url": url, "start": span[0], "end": span[1]})
    response.raise_for_status()
    lesson_id: str = response.json()["id"]
    return lesson_id


def _get_status(client: httpx.Client, lesson_id: str) -> dict[str, Any]:
    response = client.get(f"/lessons/{lesson_id}")
    response.raise_for_status()
    body: dict[str, Any] = response.json()
    return body


def _run(args: argparse.Namespace, root: Path) -> int:
    _isolate_environment(root)

    import uvicorn  # noqa: PLC0415 - phải import sau khi đặt biến môi trường

    from audio_service.main import create_app  # noqa: PLC0415

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, name="smoke-uvicorn", daemon=True)
    thread.start()
    samples: list[Sample] = []
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30.0) as client:
            if not _wait_for_health(client, time.monotonic() + HEALTH_TIMEOUT_S):
                print("JOBS FAILED: API không trả lời /health", file=sys.stderr)
                return 1
            print(f"API: 127.0.0.1:{port}, DATA_DIR tạm: {root / 'data'}, không có OPENAI_API_KEY")

            t0 = time.monotonic()
            id_a = _create(client, args.url, args.range_a)
            id_b = _create(client, args.url, args.range_b)
            print(f"LESSON_A={id_a} {args.range_a[0]:.0f}-{args.range_a[1]:.0f} s")
            print(f"LESSON_B={id_b} {args.range_b[0]:.0f}-{args.range_b[1]:.0f} s")

            ready_at: dict[str, float] = {}
            deadline = t0 + args.timeout_s
            while True:
                lesson_a = _get_status(client, id_a)
                lesson_b = _get_status(client, id_b)
                list_start = time.monotonic()
                listing = client.get("/lessons")
                latency = time.monotonic() - list_start
                listing.raise_for_status()
                now = time.monotonic() - t0
                samples.append((now, lesson_a["status"], lesson_b["status"], latency))
                for name, lesson in (("A", lesson_a), ("B", lesson_b)):
                    if lesson["status"] == "ready":
                        ready_at.setdefault(name, now)
                    elif lesson["status"] == "failed":
                        error = lesson.get("error") or {}
                        print(format_timeline(samples))
                        print(
                            f"JOBS FAILED: bài {name} lỗi ở bước '{error.get('step', '?')}': "
                            f"{error.get('message', '?')}",
                            file=sys.stderr,
                        )
                        return 1
                if len(ready_at) == 2:
                    break
                if time.monotonic() > deadline:
                    print(format_timeline(samples))
                    print(
                        f"JOBS FAILED: quá {args.timeout_s:.0f} s mà chưa xong "
                        f"({lesson_a['status']}, {lesson_b['status']})",
                        file=sys.stderr,
                    )
                    return 1
                time.sleep(POLL_INTERVAL_S)
    except httpx.HTTPError as exc:
        print(f"JOBS FAILED: lỗi HTTP: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        server.should_exit = True
        thread.join(timeout=30)

    print(format_timeline(samples))
    print()
    print(f"bài A xong sau {ready_at['A']:.1f} s, bài B xong sau {ready_at['B']:.1f} s")
    print(
        f"GET /lessons chậm nhất: {max(s[3] for s in samples) * 1000:.0f} ms ({len(samples)} mẫu)"
    )

    problems = check_timeline(samples)
    if problems:
        print("JOBS FAILED: " + "; ".join(problems), file=sys.stderr)
        return 1
    print("JOBS OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(tempfile.mkdtemp(prefix="shadowenglab-smoke-jobs-"))
    try:
        return _run(args, root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    # Thoát cứng: thread tải/model còn chạy (khi lỗi hoặc quá hạn) không được giữ process sống.
    os._exit(code)

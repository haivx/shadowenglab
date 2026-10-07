"""FastAPI app của ShadowEngLab audio service.

Bind địa chỉ không đặt ở đây: Makefile (01-08) chạy uvicorn với `--host 127.0.0.1`.
Chạy MỘT process (không `--workers N`): job runner và cổng model sống trong process này.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import partial
from typing import Literal

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from audio_service import __version__, system_status
from audio_service.config import get_settings
from audio_service.errors import error_response, install_error_handlers
from audio_service.lesson import pipeline
from audio_service.lesson.jobs import JobRunner, recover_interrupted
from audio_service.routers import (
    attempts,
    lesson,
    library,
    media,
    scoring,
    segments,
    settings,
    system,
    translate,
)

WEB_ORIGIN = "http://localhost:3000"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class Health(BaseModel):
    """Model riêng của Python, không thuộc contract (quyết định 01-01 mục 6)."""

    status: Literal["ok"]
    service: Literal["audio"]
    version: str


def create_app(
    *, deps: pipeline.PipelineDeps | None = None, warm_up: bool | None = None
) -> FastAPI:
    """`deps` tiêm stage giả cho test; mặc định dựng stage thật khi app khởi động (lifespan).

    `warm_up=None` nghĩa là "chỉ bật khi không inject deps": test dùng deps giả không bao giờ
    nạp model thật (D-18).
    """
    run_warm_up = deps is None if warm_up is None else warm_up

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # D-12: chốt thư mục dữ liệu ngay lúc khởi động; PUT /settings chỉ có hiệu lực sau restart.
        get_settings()
        resolved = deps or pipeline.default_deps()
        app.state.deps = resolved
        runner = JobRunner(
            stage_download=partial(pipeline.stage_download, deps=resolved),
            stage_model=partial(pipeline.stage_model, deps=resolved),
            mark_failed=pipeline.mark_failed,
        )
        app.state.runner = runner
        recover_interrupted()  # D-03: bài dở dang -> failed 'bị gián đoạn', không tự chạy lại
        runner.start()
        if run_warm_up:
            # Nạp -> 1 suy luận -> giải phóng từng model dưới model_gate (D-18, banner S1).
            system_status.start_warm_up(runner.model_gate)
        try:
            yield
        finally:
            runner.stop()

    app = FastAPI(title="ShadowEngLab audio service", version=__version__, lifespan=lifespan)
    install_error_handlers(app)

    @app.middleware("http")
    async def reject_foreign_origin_writes(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Pitfall 7: POST multipart là "simple request", CORS không chặn trước khi handler chạy.
        # Script/curl không gửi Origin nên không bị ảnh hưởng; trình duyệt luôn gửi Origin khi ghi.
        origin = request.headers.get("origin")
        if request.method not in SAFE_METHODS and origin is not None and origin != WEB_ORIGIN:
            return error_response(403, "forbidden_origin", "Yêu cầu không đến từ app ShadowEngLab.")
        return await call_next(request)

    # Chỉ web local được gọi (T-02-05). Add sau = bọc ngoài: CORS xử lý preflight trước guard.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[WEB_ORIGIN],
        allow_methods=["GET", "POST", "PUT", "PATCH"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )
    # Chống DNS rebinding: Host lạ -> 400.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health(status="ok", service="audio", version=__version__)

    app.include_router(lesson.router)
    app.include_router(library.router)
    app.include_router(media.router)
    app.include_router(attempts.router)
    app.include_router(segments.router)
    app.include_router(translate.router)
    app.include_router(settings.router)
    app.include_router(system.router)
    app.include_router(scoring.router)
    return app


app = create_app()

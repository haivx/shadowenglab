"""FastAPI app của ShadowEngLab audio service.

Bind địa chỉ không đặt ở đây: Makefile (01-08) chạy uvicorn với `--host 127.0.0.1`.
Chạy MỘT process (không `--workers N`): job runner và cổng model sống trong process này.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from audio_service import __version__
from audio_service.errors import install_error_handlers
from audio_service.lesson import pipeline
from audio_service.lesson.jobs import JobRunner, recover_interrupted
from audio_service.routers import lesson, scoring


class Health(BaseModel):
    """Model riêng của Python, không thuộc contract (quyết định 01-01 mục 6)."""

    status: Literal["ok"]
    service: Literal["audio"]
    version: str


def create_app(*, deps: pipeline.PipelineDeps | None = None) -> FastAPI:
    """`deps` tiêm stage giả cho test; mặc định dựng stage thật khi app khởi động (lifespan)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
        try:
            yield
        finally:
            runner.stop()

    app = FastAPI(title="ShadowEngLab audio service", version=__version__, lifespan=lifespan)
    install_error_handlers(app)
    # Chỉ web local được gọi; Phase 2 mở rộng methods khi thêm POST.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health(status="ok", service="audio", version=__version__)

    app.include_router(lesson.router)
    app.include_router(scoring.router)
    return app


app = create_app()

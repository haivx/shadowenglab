"""FastAPI app của ShadowEngLab audio service.

Bind địa chỉ không đặt ở đây: Makefile (01-08) chạy uvicorn với `--host 127.0.0.1`.
"""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from audio_service import __version__
from audio_service.routers import lesson, scoring


class Health(BaseModel):
    """Model riêng của Python, không thuộc contract (quyết định 01-01 mục 6)."""

    status: Literal["ok"]
    service: Literal["audio"]
    version: str


def create_app() -> FastAPI:
    app = FastAPI(title="ShadowEngLab audio service", version=__version__)
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

"""FastAPI app của ShadowEngLab audio service.

Bind địa chỉ không đặt ở đây: Makefile (01-08) chạy uvicorn với `--host 127.0.0.1`.
"""

from fastapi import FastAPI

from audio_service import __version__
from audio_service.routers import lesson


def create_app() -> FastAPI:
    app = FastAPI(title="ShadowEngLab audio service", version=__version__)
    app.include_router(lesson.router)
    return app


app = create_app()

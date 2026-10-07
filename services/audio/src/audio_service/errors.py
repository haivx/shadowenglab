"""Lỗi API theo hợp đồng `ApiError` {code, message tiếng Việt, lessonId?} (02-01 mục A10).

Router raise `ApiErrorException`; handler dựng body bằng model sinh từ contract để body luôn khớp
schema (field tuỳ chọn vắng thì vắng hẳn). Message là chuỗi cố định: không đường dẫn, không stack,
không echo dữ liệu người gửi (T-02-07).
"""

from __future__ import annotations

from typing import get_args

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from audio_service.contract_io import dump_contract
from audio_service.contracts_gen import ApiError

# Danh sách mã lấy từ chính model sinh ra, không chép tay.
API_ERROR_CODES: frozenset[str] = frozenset(get_args(ApiError.model_fields["code"].annotation))


class ApiErrorException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        lesson_id: str | None = None,
    ) -> None:
        super().__init__(message)
        if code not in API_ERROR_CODES:
            raise ValueError(f"mã lỗi ngoài contract: {code}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.lesson_id = lesson_id


def error_response(
    status_code: int, code: str, message: str, *, lesson_id: str | None = None
) -> JSONResponse:
    payload: dict[str, object] = {"code": code, "message": message}
    if lesson_id is not None:
        payload["lessonId"] = lesson_id
    body = dump_contract(ApiError.model_validate(payload))
    return JSONResponse(status_code=status_code, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiErrorException)
    async def _api_error(_request: Request, exc: ApiErrorException) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, lesson_id=exc.lesson_id)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Cố ý bỏ `exc.errors()`: chúng chứa input của người gửi (T-02-07).
        return error_response(422, "invalid_request", "Dữ liệu gửi lên không hợp lệ.")

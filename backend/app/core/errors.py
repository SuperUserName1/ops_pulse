import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

LOGGER = logging.getLogger(__name__)
RequestExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]


class ErrorField(BaseModel):
    field: str = Field(..., examples=["body.name"])
    message: str = Field(..., examples=["Field required"])


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["validation_error"])
    message: str = Field(..., examples=["Request validation failed."])
    fields: list[ErrorField] | None = Field(default=None)


class ErrorResponse(BaseModel):
    request_id: str = Field(..., examples=["req-123"])
    error: ErrorDetail


class AppException(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        fields: Sequence[ErrorField] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = list(fields) if fields is not None else None


def _get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return str(request_id) if request_id else "unknown"


def _build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    fields: list[ErrorField] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        request_id=_get_request_id(request),
        error=ErrorDetail(code=code, message=message, fields=fields),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(exclude_none=True),
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        fields=exc.fields,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    fields = [
        ErrorField(
            field=".".join(str(part) for part in error.get("loc", ())),
            message=str(error.get("msg", "Invalid value.")),
        )
        for error in exc.errors()
    ]
    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Request validation failed.",
        fields=fields,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    error_code = "not_found" if exc.status_code == status.HTTP_404_NOT_FOUND else "http_error"

    detail: Any = exc.detail
    message = detail if isinstance(detail, str) else "HTTP error."

    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=error_code,
        message=message,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("Unhandled exception while processing request", exc_info=exc)
    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="Internal server error.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        AppException,
        cast(RequestExceptionHandler, app_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(RequestExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(
        StarletteHTTPException,
        cast(RequestExceptionHandler, http_exception_handler),
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class ErrorDetail(BaseModel):
    code: str
    message: str
    path: str
    timestamp: str
    details: list[dict] | None = None


class AppError(Exception):
    """Base class for application errors that map to a stable error code."""

    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(code="not_found", message=message, status_code=status.HTTP_404_NOT_FOUND)


def _envelope(code: str, message: str, path: str, details: list[dict] | None = None) -> dict:
    return ErrorDetail(
        code=code,
        message=message,
        path=path,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=details,
    ).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": _envelope(exc.code, exc.message, request.url.path)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": _envelope("http_error", str(exc.detail), request.url.path)
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": _envelope(
                    "validation_error",
                    "Request validation failed",
                    request.url.path,
                    details=exc.errors(),
                )
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while processing %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": _envelope(
                    "internal_error", "An unexpected error occurred", request.url.path
                )
            },
        )

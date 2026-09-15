"""
Application-level exceptions and their FastAPI handlers.

Routers raise these instead of building HTTPException/JSON responses
inline, so every error the API returns follows the same
{"success": false, "error": {"code", "message"}} shape and Python
stack traces never leak to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class DocumentNotRelevantError(AppError):
    status_code = 422
    code = "DOCUMENT_NOT_RELEVANT"


class InvalidDocumentError(AppError):
    status_code = 400
    code = "INVALID_DOCUMENT"


class UnauthorizedError(AppError):
    status_code = 403
    code = "UNAUTHORIZED"


class AIProviderError(AppError):
    status_code = 502
    code = "AI_PROVIDER_ERROR"


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": False, "error": {"code": code, "message": message}})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        logger.warning("app_error", extra={"code": exc.code, "path": request.url.path})
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return _error_response(422, "VALIDATION_ERROR", "The request could not be validated.")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("unhandled_error", extra={"path": request.url.path})
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred. Please try again.")

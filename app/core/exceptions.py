from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500
    error_code = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AppValidationError(AppError):
    status_code = 422
    error_code = "validation_error"


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"


class AuthenticationError(AppError):
    status_code = 401
    error_code = "authentication_error"


class DocumentLoadAppError(AppError):
    status_code = 400
    error_code = "document_load_error"


class DocumentNotFoundError(AppError):
    status_code = 404
    error_code = "document_not_found"


class ChatSessionNotFoundError(AppError):
    status_code = 404
    error_code = "chat_session_not_found"


class ChunkingAppError(AppError):
    status_code = 500
    error_code = "chunking_error"


class EmbeddingAppError(AppError):
    status_code = 503
    error_code = "embedding_error"


class VectorStoreAppError(AppError):
    status_code = 503
    error_code = "vectorstore_error"


class RetrievalAppError(AppError):
    status_code = 500
    error_code = "retrieval_error"


class LLMAppError(AppError):
    status_code = 503
    error_code = "llm_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "app_error",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_error",
            extra={"request_id": request_id, "path": request.url.path},
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": {},
                    "request_id": request_id,
                }
            },
        )

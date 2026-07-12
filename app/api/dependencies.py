from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AppError
from app.core.config import settings
from app.services.auth import AuthService, AuthUser
from app.services.document import DocumentService
from app.services.chat_history import ChatHistoryService
from app.services.health import HealthService
from app.services.indexing import IndexingService
from app.services.jobs import JobService
from app.services.rag import RAGPipeline
from app.services.vectorstore.service import VectorStoreService

bearer_scheme = HTTPBearer(auto_error=False)


def _get_state_service(request: Request, name: str):
    service = getattr(request.app.state, name, None)
    if service is None:
        raise AppError(f"Service is not initialized: {name}")
    return service


def get_rag_pipeline(request: Request) -> RAGPipeline:
    return _get_state_service(request, "rag_pipeline")


def get_indexing_service(request: Request) -> IndexingService:
    return _get_state_service(request, "indexing_service")


def get_vector_store_service(request: Request) -> VectorStoreService:
    return _get_state_service(request, "vector_store_service")


def get_health_service(request: Request) -> HealthService:
    return _get_state_service(request, "health_service")


def get_document_service(request: Request) -> DocumentService:
    return _get_state_service(request, "document_service")


def get_job_service(request: Request) -> JobService:
    return _get_state_service(request, "job_service")


def get_chat_history_service(request: Request) -> ChatHistoryService:
    return _get_state_service(request, "chat_history_service")


def get_auth_service() -> AuthService:
    return AuthService(settings)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    token = credentials.credentials if credentials is not None else None
    return auth_service.verify_token(token)

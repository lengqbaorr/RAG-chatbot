from __future__ import annotations

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import require_auth
from app.api.routes import auth, chat, chat_sessions, documents, health, jobs
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, install_request_logging
from app.core.startup import lifespan


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    install_request_logging(app)
    register_exception_handlers(app)
    _install_cors(app)

    _include_routes(app, prefix="")
    _include_routes(app, prefix="/api/v1")
    return app


def _install_cors(app: FastAPI) -> None:
    origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _include_routes(app: FastAPI, *, prefix: str) -> None:
    app.include_router(health.router, prefix=prefix, tags=["health"])
    app.include_router(auth.router, prefix=prefix, tags=["auth"])
    auth_dependency = [Depends(require_auth)]
    app.include_router(chat.router, prefix=prefix, tags=["chat"], dependencies=auth_dependency)
    app.include_router(
        chat_sessions.router,
        prefix=prefix,
        tags=["chat-history"],
        dependencies=auth_dependency,
    )
    app.include_router(
        documents.router,
        prefix=prefix,
        tags=["documents"],
        dependencies=auth_dependency,
    )
    app.include_router(jobs.router, prefix=prefix, tags=["jobs"], dependencies=auth_dependency)


app = create_app()

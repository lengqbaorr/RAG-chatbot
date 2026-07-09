from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import chat, documents, health
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

    _include_routes(app, prefix="")
    _include_routes(app, prefix="/api/v1")
    return app


def _include_routes(app: FastAPI, *, prefix: str) -> None:
    app.include_router(health.router, prefix=prefix, tags=["health"])
    app.include_router(chat.router, prefix=prefix, tags=["chat"])
    app.include_router(documents.router, prefix=prefix, tags=["documents"])


app = create_app()

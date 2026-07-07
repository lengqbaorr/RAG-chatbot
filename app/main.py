from fastapi import FastAPI

from app.api.routes import health
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    return app


app = create_app()

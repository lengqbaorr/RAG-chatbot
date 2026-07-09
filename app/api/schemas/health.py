from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    app: str
    embedding_service: str
    vector_store: str
    llm_provider: str
    collection: str | None = None
    collection_count: int = Field(..., ge=0)
    ready: bool

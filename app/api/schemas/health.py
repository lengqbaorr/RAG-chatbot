from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    app: str
    database: str = "unknown"
    embedding_service: str
    vector_store: str
    llm_provider: str
    upload_dir: str | None = None
    disk_free_bytes: int | None = None
    collection: str | None = None
    collection_count: int = Field(..., ge=0)
    pending_jobs: int = Field(default=0, ge=0)
    ready: bool

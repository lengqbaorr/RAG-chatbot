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
    embedding_model: str | None = None
    embedding_model_loaded: bool = False
    embedding_model_cached: bool = False
    reranker_model: str | None = None
    reranker_model_loaded: bool = False
    reranker_model_cached: bool = False
    reranker_available: bool = False
    ready: bool

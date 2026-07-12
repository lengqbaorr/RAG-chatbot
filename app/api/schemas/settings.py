from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    app_name: str
    app_version: str
    environment: str
    auth_enabled: bool
    llm_provider: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    retrieval_strategy: str
    top_k: int
    fetch_k: int
    min_score: float
    reranker_enabled: bool
    reranker_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    chroma_collection: str


class SettingsUpdateRequest(BaseModel):
    llm_model: str | None = Field(default=None, min_length=1, max_length=120)
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=None, ge=1, le=8192)
    retrieval_strategy: str | None = Field(default=None, pattern="^(dense|parent_child)$")
    top_k: int | None = Field(default=None, ge=1, le=20)
    fetch_k: int | None = Field(default=None, ge=1, le=100)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reranker_enabled: bool | None = None
    reranker_model: str | None = Field(default=None, min_length=1, max_length=160)

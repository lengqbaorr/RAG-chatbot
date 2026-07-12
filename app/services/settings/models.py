from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeSettings:
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


@dataclass(frozen=True)
class UserSettingsUpdate:
    llm_model: str | None = None
    llm_temperature: float | None = None
    llm_max_tokens: int | None = None
    retrieval_strategy: str | None = None
    top_k: int | None = None
    fetch_k: int | None = None
    min_score: float | None = None
    reranker_enabled: bool | None = None
    reranker_model: str | None = None

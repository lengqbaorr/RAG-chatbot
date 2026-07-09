from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.retrieval.models import RetrievedChunk


class RerankedChunk(BaseModel):
    chunk: RetrievedChunk
    original_rank: int = Field(..., ge=1)
    original_score: float = Field(..., ge=0.0, le=1.0)
    rerank_score: float
    final_rank: int = Field(..., ge=1)


class RerankResult(BaseModel):
    query: str
    chunks: list[RerankedChunk] = Field(default_factory=list)
    provider: str
    model: str

from __future__ import annotations

from dataclasses import dataclass

from app.services.retrieval.models import RetrievedChunk


@dataclass(frozen=True)
class RerankerConfig:
    model_name: str = "BAAI/bge-reranker-v2-m3"
    device: str = "cpu"
    local_files_only: bool = False


@dataclass(frozen=True)
class RerankedChunk:
    chunk: RetrievedChunk
    rerank_score: float
    original_score: float
    original_rank: int

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.reranking.models import RerankedChunk
from app.services.retrieval.models import RetrievedChunk


class BaseReranker(ABC):
    @abstractmethod
    def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RerankedChunk]:
        raise NotImplementedError

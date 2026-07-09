from app.services.reranking.config import RerankerConfig
from app.services.reranking.interfaces import BaseReranker
from app.services.reranking.models import RerankedChunk, RerankResult
from app.services.reranking.service import RerankerService, RerankingRetrieverAdapter


def __getattr__(name: str):
    if name in {"BGERerankerError", "BGERerankerProvider"}:
        from app.services.reranking.providers.bge_reranker_provider import (
            BGERerankerError,
            BGERerankerProvider,
        )

        return {
            "BGERerankerError": BGERerankerError,
            "BGERerankerProvider": BGERerankerProvider,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseReranker",
    "BGERerankerError",
    "BGERerankerProvider",
    "RerankedChunk",
    "RerankerConfig",
    "RerankerService",
    "RerankingRetrieverAdapter",
    "RerankResult",
]

from __future__ import annotations

from app.services.reranking.config import RerankerConfig
from app.services.reranking.interfaces import BaseReranker
from app.services.reranking.models import RerankResult, RerankedChunk
from app.services.retrieval.models import RetrievedChunk, RetrievalResult


class RerankerService:
    def __init__(self, *, reranker: BaseReranker, config: RerankerConfig | None = None) -> None:
        self.reranker = reranker
        self.config = config or RerankerConfig(
            provider=reranker.provider_name,
            model_name=reranker.model_name,
        )

    def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> RerankResult:
        reranked = self.reranker.rerank(query=query, chunks=chunks, top_k=top_k)
        return RerankResult(
            query=query,
            chunks=reranked,
            provider=self.reranker.provider_name,
            model=self.reranker.model_name,
        )


class RerankingRetrieverAdapter:
    def __init__(self, *, retriever, reranker: BaseReranker | RerankerService, rerank_top_k: int) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.rerank_top_k = rerank_top_k

    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        result = self.retriever.retrieve(query, **kwargs)
        if isinstance(self.reranker, RerankerService):
            reranked = self.reranker.rerank(
                query=query,
                chunks=result.chunks,
                top_k=self.rerank_top_k,
            ).chunks
        else:
            reranked = self.reranker.rerank(
                query=query,
                chunks=result.chunks,
                top_k=self.rerank_top_k,
            )
        chunks = [self._apply_rerank_metadata(item) for item in reranked]
        return result.model_copy(
            update={
                "chunks": chunks,
                "context": result.context.model_copy(update={"chunks": chunks}),
            }
        )

    def _apply_rerank_metadata(self, item: RerankedChunk) -> RetrievedChunk:
        metadata = dict(item.chunk.metadata)
        metadata["original_rank"] = item.original_rank
        metadata["original_score"] = item.original_score
        metadata["rerank_score"] = item.rerank_score
        return item.chunk.model_copy(
            update={
                "rank": item.final_rank,
                "score": item.chunk.score,
                "metadata": metadata,
            }
        )

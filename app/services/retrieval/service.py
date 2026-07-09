from __future__ import annotations

from app.services.embedding.service import EmbeddingService
from app.services.retrieval.config import ParentChildRetrievalConfig, RetrievalConfig
from app.services.retrieval.interfaces import BaseRetriever
from app.services.retrieval.models import RetrievalQuery, RetrievalResult
from app.services.retrieval.retrievers import DenseRetriever, ParentChildRetriever
from app.services.vectorstore.interfaces import BaseVectorStore


class RetrievalService:
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
        retrievers: dict[str, BaseRetriever] | None = None,
        dense_config: RetrievalConfig | None = None,
        parent_child_config: ParentChildRetrievalConfig | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.retrievers = retrievers or {
            "dense": DenseRetriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
                config=dense_config or RetrievalConfig(),
            ),
            "parent_child": ParentChildRetriever(
                embedding_service=embedding_service,
                vector_store=vector_store,
                config=parent_child_config or ParentChildRetrievalConfig(),
            ),
        }

    def retrieve(
        self,
        query: str | RetrievalQuery,
        *,
        strategy: str = "dense",
        filters: dict | None = None,
        top_k: int | None = None,
        fetch_k: int | None = None,
        min_score: float | None = None,
    ) -> RetrievalResult:
        retrieval_query = self._build_query(
            query,
            strategy=strategy,
            filters=filters,
            top_k=top_k,
            fetch_k=fetch_k,
            min_score=min_score,
        )
        selected_strategy = retrieval_query.strategy or strategy
        retriever = self.retrievers.get(selected_strategy)
        if retriever is None:
            raise ValueError(f"Unsupported retrieval strategy: {selected_strategy}")
        return retriever.retrieve(retrieval_query)

    def _build_query(
        self,
        query: str | RetrievalQuery,
        *,
        strategy: str,
        filters: dict | None,
        top_k: int | None,
        fetch_k: int | None,
        min_score: float | None,
    ) -> RetrievalQuery:
        if isinstance(query, RetrievalQuery):
            return query.model_copy(
                update={
                    "strategy": query.strategy or strategy,
                    "filters": query.filters if query.filters is not None else filters,
                    "top_k": query.top_k or top_k,
                    "fetch_k": query.fetch_k or fetch_k,
                    "min_score": query.min_score if query.min_score is not None else min_score,
                }
            )

        return RetrievalQuery(
            query=query,
            strategy=strategy,
            filters=filters,
            top_k=top_k,
            fetch_k=fetch_k,
            min_score=min_score,
        )

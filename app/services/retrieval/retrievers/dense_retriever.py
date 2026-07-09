from __future__ import annotations

import time

from app.services.embedding.service import EmbeddingService
from app.services.retrieval.config import RetrievalConfig
from app.services.retrieval.context_selector import ContextSelector
from app.services.retrieval.deduplicator import RetrievalDeduplicator
from app.services.retrieval.filters import ContentTypeFilter, ScoreThresholdFilter
from app.services.retrieval.interfaces import BaseRetriever
from app.services.retrieval.models import (
    RetrievedChunk,
    RetrievedContext,
    RetrievalQuery,
    RetrievalReport,
    RetrievalResult,
)
from app.services.retrieval.postprocessor import RetrievalPostProcessor
from app.services.retrieval.query_preprocessor import QueryPreprocessor
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import VectorSearchResult


class DenseRetriever(BaseRetriever):
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
        config: RetrievalConfig | None = None,
        query_preprocessor: QueryPreprocessor | None = None,
        postprocessor: RetrievalPostProcessor | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.config = config or RetrievalConfig()
        self.query_preprocessor = query_preprocessor or QueryPreprocessor(
            lowercase=self.config.lowercase_query,
            remove_noisy_punctuation=self.config.remove_noisy_punctuation,
        )
        self.postprocessor = postprocessor

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        started = time.perf_counter()
        config = self._effective_config(query)
        normalized_query = self.query_preprocessor.normalize(query.query)

        embedding_started = time.perf_counter()
        query_vector = self.embedding_service.embed_query(normalized_query)
        embedding_time = time.perf_counter() - embedding_started

        vector_started = time.perf_counter()
        vector_results = self.vector_store.similarity_search(
            query_vector=query_vector,
            top_k=config.fetch_k,
            filters=self._merge_filters(config.filters, query.filters),
        )
        vector_search_time = time.perf_counter() - vector_started

        retrieved = [
            self._from_vector_result(result, rank=index, strategy=config.strategy)
            for index, result in enumerate(vector_results, start=1)
        ]
        postprocessor = self.postprocessor or self._build_postprocessor(config)
        processed = postprocessor.process(retrieved, top_k=config.top_k)
        retrieval_time = time.perf_counter() - started

        report = self._build_report(
            query=query.query,
            normalized_query=normalized_query,
            config=config,
            initial_results=len(retrieved),
            after_threshold=processed.after_threshold,
            after_dedup=processed.after_dedup,
            final_chunks=processed.chunks,
            embedding_time=embedding_time,
            vector_search_time=vector_search_time,
            retrieval_time=retrieval_time,
        )
        context = RetrievedContext(
            query=query.query,
            normalized_query=normalized_query,
            strategy=config.strategy,
            chunks=processed.chunks,
        )
        return RetrievalResult(
            query=query.query,
            normalized_query=normalized_query,
            context=context,
            chunks=processed.chunks,
            report=report,
        )

    def _effective_config(self, query: RetrievalQuery) -> RetrievalConfig:
        return RetrievalConfig(
            strategy=query.strategy or self.config.strategy,
            top_k=query.top_k or self.config.top_k,
            fetch_k=query.fetch_k or self.config.fetch_k,
            min_score=query.min_score if query.min_score is not None else self.config.min_score,
            filters=self.config.filters,
            deduplicate_by=self.config.deduplicate_by,
            exclude_content_types=self.config.exclude_content_types,
            include_chunk_levels=self.config.include_chunk_levels,
            lowercase_query=self.config.lowercase_query,
            remove_noisy_punctuation=self.config.remove_noisy_punctuation,
        )

    def _build_postprocessor(self, config: RetrievalConfig) -> RetrievalPostProcessor:
        return RetrievalPostProcessor(
            threshold_filter=ScoreThresholdFilter(config.min_score),
            content_type_filter=ContentTypeFilter(
                exclude_content_types=config.exclude_content_types,
                include_chunk_levels=config.include_chunk_levels,
            ),
            deduplicator=RetrievalDeduplicator(config.deduplicate_by),
            context_selector=ContextSelector(),
        )

    def _from_vector_result(
        self,
        result: VectorSearchResult,
        *,
        rank: int,
        strategy: str,
    ) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            source_id=result.source_id,
            content=result.content,
            metadata=result.metadata,
            score=result.score,
            distance=result.distance,
            rank=rank,
            source_name=result.source_name,
            source_type=result.source_type,
            page_start=result.page_start,
            page_end=result.page_end,
            section_title=result.section_title,
            header_path=result.header_path,
            header_path_text=result.header_path_text,
            content_type=result.content_type,
            chunk_level=result.chunk_level,
            parent_id=result.parent_id,
            child_ids=result.child_ids,
            retrieval_strategy=strategy,
        )

    def _merge_filters(self, base: dict | None, override: dict | None) -> dict | None:
        merged: dict = {}
        if base:
            merged.update(base)
        if override:
            merged.update(override)
        return merged or None

    def _build_report(
        self,
        *,
        query: str,
        normalized_query: str,
        config: RetrievalConfig,
        initial_results: int,
        after_threshold: int,
        after_dedup: int,
        final_chunks: list[RetrievedChunk],
        embedding_time: float,
        vector_search_time: float,
        retrieval_time: float,
    ) -> RetrievalReport:
        scores = [chunk.score for chunk in final_chunks]
        return RetrievalReport(
            query=query,
            normalized_query=normalized_query,
            top_k=config.top_k,
            fetch_k=config.fetch_k,
            initial_results=initial_results,
            after_threshold=after_threshold,
            after_dedup=after_dedup,
            final_results=len(final_chunks),
            min_score=round(min(scores), 4) if scores else 0.0,
            max_score=round(max(scores), 4) if scores else 0.0,
            avg_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
            embedding_time=round(embedding_time, 6),
            vector_search_time=round(vector_search_time, 6),
            retrieval_time=round(retrieval_time, 6),
            strategy=config.strategy,
        )

from __future__ import annotations

import time

from app.services.embedding.service import EmbeddingService
from app.services.retrieval.config import ParentChildRetrievalConfig
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
from app.services.vectorstore.models import VectorRecord, VectorSearchResult


class ParentChildRetriever(BaseRetriever):
    def __init__(
        self,
        *,
        embedding_service: EmbeddingService,
        vector_store: BaseVectorStore,
        config: ParentChildRetrievalConfig | None = None,
        query_preprocessor: QueryPreprocessor | None = None,
        postprocessor: RetrievalPostProcessor | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.config = config or ParentChildRetrievalConfig()
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
            top_k=config.child_fetch_k,
            filters=self._child_filters(config, query.filters),
        )
        vector_search_time = time.perf_counter() - vector_started

        child_chunks = [
            self._from_vector_result(result, rank=index, strategy=config.strategy)
            for index, result in enumerate(vector_results, start=1)
        ]
        postprocessor = self.postprocessor or self._build_postprocessor(config)
        processed_children = postprocessor.process(
            child_chunks,
            top_k=config.parent_top_k,
        )
        final_chunks = self._expand_parents(processed_children.chunks, config)
        final_chunks = [
            chunk.model_copy(update={"rank": rank})
            for rank, chunk in enumerate(final_chunks[: config.parent_top_k], start=1)
        ]
        retrieval_time = time.perf_counter() - started

        report = self._build_report(
            query=query.query,
            normalized_query=normalized_query,
            config=config,
            initial_results=len(child_chunks),
            after_threshold=processed_children.after_threshold,
            after_dedup=processed_children.after_dedup,
            final_chunks=final_chunks,
            embedding_time=embedding_time,
            vector_search_time=vector_search_time,
            retrieval_time=retrieval_time,
        )
        context = RetrievedContext(
            query=query.query,
            normalized_query=normalized_query,
            strategy=config.strategy,
            chunks=final_chunks,
        )
        return RetrievalResult(
            query=query.query,
            normalized_query=normalized_query,
            context=context,
            chunks=final_chunks,
            report=report,
        )

    def _effective_config(self, query: RetrievalQuery) -> ParentChildRetrievalConfig:
        return ParentChildRetrievalConfig(
            top_k=query.top_k or self.config.top_k,
            fetch_k=query.fetch_k or self.config.fetch_k,
            min_score=query.min_score if query.min_score is not None else self.config.min_score,
            filters=self.config.filters,
            exclude_content_types=self.config.exclude_content_types,
            include_chunk_levels=self.config.include_chunk_levels,
            lowercase_query=self.config.lowercase_query,
            remove_noisy_punctuation=self.config.remove_noisy_punctuation,
            child_fetch_k=query.fetch_k or self.config.child_fetch_k,
            parent_top_k=query.top_k or self.config.parent_top_k,
            fallback_to_child=self.config.fallback_to_child,
        )

    def _build_postprocessor(self, config: ParentChildRetrievalConfig) -> RetrievalPostProcessor:
        return RetrievalPostProcessor(
            threshold_filter=ScoreThresholdFilter(config.min_score),
            content_type_filter=ContentTypeFilter(
                exclude_content_types=config.exclude_content_types,
                include_chunk_levels=("child",),
            ),
            deduplicator=RetrievalDeduplicator("parent_id"),
            context_selector=ContextSelector(),
        )

    def _child_filters(
        self,
        config: ParentChildRetrievalConfig,
        query_filters: dict | None,
    ) -> dict:
        filters: dict = {}
        if config.filters:
            filters.update(config.filters)
        if query_filters:
            filters.update(query_filters)
        filters["chunk_level"] = "child"
        return filters

    def _expand_parents(
        self,
        child_chunks: list[RetrievedChunk],
        config: ParentChildRetrievalConfig,
    ) -> list[RetrievedChunk]:
        expanded: list[RetrievedChunk] = []
        for child in child_chunks:
            parent = self._get_parent(child)
            if parent is not None:
                expanded.append(self._from_parent_record(parent, child, config.strategy))
                continue
            if config.fallback_to_child:
                expanded.append(
                    child.model_copy(
                        update={
                            "retrieval_strategy": config.strategy,
                            "retrieved_child": child,
                            "child_score": child.score,
                            "parent_content": None,
                        }
                    )
                )
        return expanded

    def _get_parent(self, child: RetrievedChunk) -> VectorRecord | None:
        if not child.parent_id:
            return None
        return self.vector_store.get_by_chunk_id(child.parent_id)

    def _from_parent_record(
        self,
        parent: VectorRecord,
        child: RetrievedChunk,
        strategy: str,
    ) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=parent.chunk_id,
            document_id=parent.document_id,
            source_id=parent.source_id,
            content=parent.content,
            metadata=parent.metadata,
            score=child.score,
            distance=child.distance,
            rank=child.rank,
            source_name=parent.source_name,
            source_type=parent.source_type,
            page_start=parent.page_start or child.page_start,
            page_end=parent.page_end or child.page_end,
            section_title=parent.section_title or child.section_title,
            header_path=parent.header_path or child.header_path,
            header_path_text=parent.header_path_text or child.header_path_text,
            content_type=parent.content_type,
            chunk_level=parent.chunk_level,
            parent_id=parent.parent_id,
            child_ids=parent.child_ids,
            retrieval_strategy=strategy,
            retrieved_child=child,
            child_score=child.score,
            parent_content=parent.content,
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

    def _build_report(
        self,
        *,
        query: str,
        normalized_query: str,
        config: ParentChildRetrievalConfig,
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
            top_k=config.parent_top_k,
            fetch_k=config.child_fetch_k,
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

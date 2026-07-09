from __future__ import annotations

import pytest

from app.services.retrieval import (
    ContextSelector,
    DenseRetriever,
    ParentChildRetriever,
    ParentChildRetrievalConfig,
    QueryPreprocessor,
    RetrievedChunk,
    RetrievalConfig,
    RetrievalDeduplicator,
    RetrievalQuery,
    RetrievalService,
    ScoreThresholdFilter,
)
from app.services.retrieval.interfaces import BaseRetriever
from app.services.retrieval.models import RetrievalResult
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreDeleteResult,
    VectorStoreStats,
    VectorStoreUpsertResult,
)


class FakeEmbeddingService:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1, 0.2, 0.3, 0.4]


class FakeVectorStore(BaseVectorStore):
    def __init__(
        self,
        results: list[VectorSearchResult] | None = None,
        records: dict[str, VectorRecord] | None = None,
    ) -> None:
        self.results = results or []
        self.records = records or {}
        self.last_query_vector: list[float] | None = None
        self.last_top_k: int | None = None
        self.last_filters: dict | None = None

    def upsert(self, records: list[VectorRecord]) -> VectorStoreUpsertResult:
        for record in records:
            self.records[record.chunk_id] = record
        return VectorStoreUpsertResult(
            total_input=len(records),
            skipped_excluded=0,
            upserted_count=len(records),
            failed_count=0,
            collection_name="fake",
        )

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        self.last_query_vector = query_vector
        self.last_top_k = top_k
        self.last_filters = filters
        return self.results[:top_k]

    def delete_by_document_id(self, document_id: str) -> VectorStoreDeleteResult:
        return VectorStoreDeleteResult(deleted_count=0)

    def delete_by_source_id(self, source_id: str) -> VectorStoreDeleteResult:
        return VectorStoreDeleteResult(deleted_count=0)

    def delete_by_chunk_ids(self, chunk_ids: list[str]) -> VectorStoreDeleteResult:
        return VectorStoreDeleteResult(deleted_count=0)

    def get_by_chunk_id(self, chunk_id: str) -> VectorRecord | None:
        return self.records.get(chunk_id)

    def count(self, filters: dict | None = None) -> int:
        return len(self.records)

    def stats(self) -> VectorStoreStats:
        return VectorStoreStats(
            total_count=len(self.records),
            collection_name="fake",
            embedding_model="fake",
            embedding_dimension=4,
            distance_metric="cosine",
        )


class FakeRoutingRetriever(BaseRetriever):
    def __init__(self, strategy: str) -> None:
        self.strategy = strategy
        self.called = False

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.called = True
        report = {
            "query": query.query,
            "normalized_query": query.query,
            "top_k": 1,
            "fetch_k": 1,
            "initial_results": 0,
            "after_threshold": 0,
            "after_dedup": 0,
            "final_results": 0,
            "retrieval_time": 0.0,
            "embedding_time": 0.0,
            "vector_search_time": 0.0,
            "strategy": self.strategy,
        }
        return RetrievalResult(
            query=query.query,
            normalized_query=query.query,
            context={
                "query": query.query,
                "normalized_query": query.query,
                "strategy": self.strategy,
                "chunks": [],
            },
            chunks=[],
            report=report,
        )


def _result(
    chunk_id: str,
    *,
    score: float = 0.9,
    content_type: str = "body",
    chunk_level: str = "child",
    parent_id: str | None = None,
    content_hash: str | None = None,
    page_start: int | None = 1,
    page_end: int | None = 1,
) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=f"Content for {chunk_id}",
        embedding_text="",
        metadata={"content_hash": content_hash or f"hash-{chunk_id}"},
        score=score,
        distance=1.0 - score,
        source_name="doc.pdf",
        source_type="pdf",
        page_start=page_start,
        page_end=page_end,
        section_title="Section",
        header_path=["Section"],
        header_path_text="Section",
        content_type=content_type,
        chunk_level=chunk_level,
        parent_id=parent_id,
        child_ids=[],
        embedding_provider="fake",
        embedding_model="fake",
        embedding_dimension=4,
        embedding_version="v1",
        embedding_text_hash=f"eh-{chunk_id}",
    )


def _record(
    chunk_id: str,
    *,
    content: str = "Parent content",
    chunk_level: str = "parent",
) -> VectorRecord:
    return VectorRecord(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=content,
        embedding_text="",
        vector=[0.1, 0.2, 0.3, 0.4],
        metadata={"content_hash": f"hash-{chunk_id}"},
        source_name="doc.pdf",
        source_type="pdf",
        page_start=1,
        page_end=3,
        section_title="Parent Section",
        header_path=["Parent Section"],
        header_path_text="Parent Section",
        content_type="body",
        chunk_level=chunk_level,
        parent_id=None,
        child_ids=["c1", "c2"],
        embedding_provider="fake",
        embedding_model="fake",
        embedding_dimension=4,
        embedding_version="v1",
        embedding_text_hash=f"eh-{chunk_id}",
    )


def _chunk(
    chunk_id: str,
    *,
    score: float = 0.9,
    parent_id: str | None = None,
    content_type: str = "body",
    chunk_level: str = "child",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=f"Content {chunk_id}",
        metadata={"content_hash": f"hash-{chunk_id}"},
        score=score,
        distance=1.0 - score,
        rank=1,
        source_name="doc.pdf",
        source_type="pdf",
        page_start=1,
        page_end=1,
        section_title="Section",
        header_path=["Section"],
        content_type=content_type,
        chunk_level=chunk_level,
        parent_id=parent_id,
        retrieval_strategy="dense",
    )


def test_query_preprocessor_normalizes_whitespace_and_punctuation() -> None:
    normalized = QueryPreprocessor().normalize(
        "   Bông tuyết Koch   được xây dựng như thế nào??? "
    )

    assert normalized == "Bông tuyết Koch được xây dựng như thế nào?"


def test_query_preprocessor_preserves_vietnamese_numbers_and_codes() -> None:
    normalized = QueryPreprocessor().normalize("  Mục 2.1 và file CS105.Q22.pdf?? ")

    assert "2.1" in normalized
    assert "CS105.Q22.pdf" in normalized


def test_empty_query_raises() -> None:
    with pytest.raises(ValueError):
        RetrievalQuery(query="   ")


def test_score_threshold_filter() -> None:
    chunks = [_chunk("c1", score=0.7), _chunk("c2", score=0.4)]

    filtered = ScoreThresholdFilter(0.6).apply(chunks)

    assert [chunk.chunk_id for chunk in filtered] == ["c1"]


def test_deduplicator_by_chunk_id() -> None:
    chunks = [_chunk("c1"), _chunk("c1"), _chunk("c2")]

    deduped = RetrievalDeduplicator("chunk_id").apply(chunks)

    assert [chunk.chunk_id for chunk in deduped] == ["c1", "c2"]


def test_deduplicator_by_parent_id() -> None:
    chunks = [
        _chunk("c1", parent_id="p1"),
        _chunk("c2", parent_id="p1"),
        _chunk("c3", parent_id="p2"),
    ]

    deduped = RetrievalDeduplicator("parent_id").apply(chunks)

    assert [chunk.chunk_id for chunk in deduped] == ["c1", "c3"]


def test_context_selector_sorts_and_limits_top_k() -> None:
    chunks = [
        _chunk("c1", score=0.5),
        _chunk("c2", score=0.9),
        _chunk("c3", score=0.7),
    ]

    selected = ContextSelector().select(chunks, top_k=2)

    assert [chunk.chunk_id for chunk in selected] == ["c2", "c3"]
    assert [chunk.rank for chunk in selected] == [1, 2]


def test_dense_retriever_pipeline_with_mock_services() -> None:
    embedding = FakeEmbeddingService()
    store = FakeVectorStore(
        results=[
            _result("c1", score=0.9),
            _result("c2", score=0.7),
            _result("c3", score=0.2),
        ]
    )
    retriever = DenseRetriever(
        embedding_service=embedding,
        vector_store=store,
        config=RetrievalConfig(top_k=2, fetch_k=3, min_score=0.5),
    )

    result = retriever.retrieve(RetrievalQuery(query="  Query??? "))

    assert embedding.queries == ["Query?"]
    assert store.last_top_k == 3
    assert [chunk.chunk_id for chunk in result.chunks] == ["c1", "c2"]
    assert result.report.initial_results == 3
    assert result.report.after_threshold == 2
    assert result.report.final_results == 2


def test_dense_retriever_metadata_filter_passthrough() -> None:
    store = FakeVectorStore(results=[_result("c1")])
    retriever = DenseRetriever(
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
        config=RetrievalConfig(filters={"source_type": "pdf"}),
    )

    retriever.retrieve(
        RetrievalQuery(query="Koch", filters={"content_type": "body"})
    )

    assert store.last_filters == {"source_type": "pdf", "content_type": "body"}


def test_dense_retriever_excludes_cover_and_toc() -> None:
    store = FakeVectorStore(
        results=[
            _result("cover", score=0.99, content_type="cover"),
            _result("toc", score=0.98, content_type="toc"),
            _result("body", score=0.5, content_type="body"),
        ]
    )
    retriever = DenseRetriever(
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
        config=RetrievalConfig(top_k=3, fetch_k=3),
    )

    result = retriever.retrieve(RetrievalQuery(query="Koch"))

    assert [chunk.chunk_id for chunk in result.chunks] == ["body"]


def test_parent_child_retriever_expands_parent() -> None:
    store = FakeVectorStore(
        results=[
            _result("c1", score=0.9, parent_id="p1"),
            _result("c2", score=0.8, parent_id="p1"),
        ],
        records={"p1": _record("p1", content="Expanded parent content")},
    )
    retriever = ParentChildRetriever(
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
        config=ParentChildRetrievalConfig(parent_top_k=2, child_fetch_k=5),
    )

    result = retriever.retrieve(RetrievalQuery(query="Koch"))

    assert store.last_filters["chunk_level"] == "child"
    assert len(result.chunks) == 1
    assert result.chunks[0].chunk_id == "p1"
    assert result.chunks[0].retrieved_child is not None
    assert result.chunks[0].child_score == 0.9


def test_parent_child_retriever_fallback_to_child() -> None:
    store = FakeVectorStore(results=[_result("c1", score=0.9, parent_id="missing")])
    retriever = ParentChildRetriever(
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
        config=ParentChildRetrievalConfig(parent_top_k=1, child_fetch_k=5),
    )

    result = retriever.retrieve(RetrievalQuery(query="Koch"))

    assert len(result.chunks) == 1
    assert result.chunks[0].chunk_id == "c1"
    assert result.chunks[0].retrieved_child is not None


def test_retrieval_service_strategy_routing() -> None:
    dense = FakeRoutingRetriever("dense")
    parent = FakeRoutingRetriever("parent_child")
    service = RetrievalService(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
        retrievers={"dense": dense, "parent_child": parent},
    )

    result = service.retrieve("Koch", strategy="parent_child")

    assert parent.called is True
    assert dense.called is False
    assert result.report.strategy == "parent_child"

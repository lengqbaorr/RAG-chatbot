from __future__ import annotations

from app.services.reranking.interfaces import BaseReranker
from app.services.reranking.models import RerankedChunk
from app.services.reranking.service import RerankerService, RerankingRetrieverAdapter
from app.services.retrieval.models import RetrievedChunk, RetrievedContext, RetrievalReport, RetrievalResult


class MockReranker(BaseReranker):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-reranker"

    def rerank(self, query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RerankedChunk]:
        del query
        scores = {"c1": 0.1, "c2": 0.9, "c3": 0.5}
        items = [
            RerankedChunk(
                chunk=chunk,
                original_rank=chunk.rank,
                original_score=chunk.score,
                rerank_score=scores[chunk.chunk_id],
                final_rank=1,
            )
            for chunk in chunks
        ]
        items.sort(key=lambda item: item.rerank_score, reverse=True)
        return [item.model_copy(update={"final_rank": index}) for index, item in enumerate(items[:top_k], 1)]


class FakeRetriever:
    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        del kwargs
        chunks = [_chunk("c1", 1, 0.95), _chunk("c2", 2, 0.8), _chunk("c3", 3, 0.7)]
        return RetrievalResult(
            query=query,
            normalized_query=query,
            context=RetrievedContext(query=query, normalized_query=query, strategy="dense", chunks=chunks),
            chunks=chunks,
            report=RetrievalReport(
                query=query,
                normalized_query=query,
                top_k=3,
                fetch_k=20,
                initial_results=3,
                after_threshold=3,
                after_dedup=3,
                final_results=3,
                retrieval_time=0.01,
                embedding_time=0.001,
                vector_search_time=0.002,
                strategy="dense",
            ),
        )


def _chunk(chunk_id: str, rank: int, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=f"Content {chunk_id}",
        metadata={},
        score=score,
        distance=1.0 - score,
        rank=rank,
        source_name="doc.pdf",
        source_type="pdf",
        page_start=1,
        page_end=1,
        section_title="Section",
        header_path=["Section"],
        content_type="body",
        chunk_level="child",
        retrieval_strategy="dense",
    )


def test_reranker_service_sorts_and_preserves_original_score() -> None:
    service = RerankerService(reranker=MockReranker())

    result = service.rerank(query="Koch", chunks=[_chunk("c1", 1, 0.95), _chunk("c2", 2, 0.8)], top_k=2)

    assert [item.chunk.chunk_id for item in result.chunks] == ["c2", "c1"]
    assert result.chunks[0].original_score == 0.8
    assert result.chunks[0].rerank_score == 0.9


def test_reranking_retriever_adapter_updates_rank_and_metadata() -> None:
    adapter = RerankingRetrieverAdapter(
        retriever=FakeRetriever(),
        reranker=MockReranker(),
        rerank_top_k=2,
    )

    result = adapter.retrieve("Koch", strategy="dense", top_k=3, fetch_k=20, min_score=0.0)

    assert [chunk.chunk_id for chunk in result.chunks] == ["c2", "c3"]
    assert [chunk.rank for chunk in result.chunks] == [1, 2]
    assert result.chunks[0].metadata["original_score"] == 0.8
    assert result.chunks[0].metadata["rerank_score"] == 0.9

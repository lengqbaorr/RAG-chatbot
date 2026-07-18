from __future__ import annotations

from app.services.benchmark import (
    BenchmarkCase,
    BenchmarkConfig,
    evaluate_retrieval_case,
    load_benchmark_dataset,
    summarize_results,
)
from app.services.benchmark.metrics import score_chunk_relevance
from app.services.retrieval.models import RetrievedChunk, RetrievedContext, RetrievalReport, RetrievalResult
from app.cli.benchmark import _slice_cases


def test_load_benchmark_dataset_from_jsonl(tmp_path) -> None:
    dataset = tmp_path / "eval.jsonl"
    dataset.write_text(
        '{"id":"q1","question":"Vector Space Model là gì?","expected_source_name":"Test.pdf","expected_pages":[1],"expected_keywords":["vector"],"answerable":true}\n',
        encoding="utf-8",
    )

    cases = load_benchmark_dataset(dataset)

    assert len(cases) == 1
    assert cases[0].id == "q1"


def test_relevance_matches_source_page_and_keywords() -> None:
    case = BenchmarkCase(
        id="q1",
        question="Vector Space Model là gì?",
        expected_source_name="Test.pdf",
        expected_pages=[24],
        expected_keywords=["vector", "truy xuất thông tin"],
    )

    score = score_chunk_relevance(case, _chunk("c1"))

    assert score.source_match is True
    assert score.page_match_score == 1.0
    assert score.keyword_match_score == 1.0
    assert score.relevant is True


def test_relevance_allows_page_tolerance() -> None:
    case = BenchmarkCase(
        id="q1",
        question="Lời cảm ơn ở đâu?",
        expected_source_name="Test.pdf",
        expected_pages=[23],
    )

    score = score_chunk_relevance(case, _chunk("c1"), page_tolerance=1)

    assert score.page_match_score == 1.0
    assert score.relevant is True


def test_relevance_matches_split_section_label() -> None:
    case = BenchmarkCase(
        id="q1",
        question="Nhóm gồm ai?",
        expected_section="Trang bìa / Vector Space Model",
    )

    score = score_chunk_relevance(case, _chunk("c1"))

    assert score.section_match_score == 1.0
    assert score.relevant is True


def test_evaluate_and_summarize_retrieval_metrics() -> None:
    config = BenchmarkConfig(strategy="dense", top_k=3, fetch_k=8, min_score=0.7)
    case = BenchmarkCase(
        id="q1",
        question="Vector Space Model là gì?",
        expected_source_name="Test.pdf",
        expected_pages=[24],
        expected_keywords=["vector"],
    )
    result = evaluate_retrieval_case(case, _retrieval_result([_chunk("c1")]), config=config)
    report = summarize_results([result], config=config)

    assert result.hit_rank == 1
    assert report.recall_at_1 == 1.0
    assert report.mrr == 1.0
    assert report.failed_cases == []


def test_benchmark_slice_cases_with_offset_and_limit() -> None:
    cases = [
        BenchmarkCase(id=f"q{index}", question=f"Question {index}", expected_keywords=["x"])
        for index in range(5)
    ]

    selected = _slice_cases(cases, offset=2, limit=2)

    assert [case.id for case in selected] == ["q2", "q3"]


def _chunk(chunk_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content="Vector Space Model biểu diễn tài liệu thành vector để truy xuất thông tin.",
        metadata={},
        score=0.9,
        distance=0.1,
        rank=1,
        source_name="Test.pdf",
        source_type="pdf",
        page_start=24,
        page_end=24,
        section_title="Vector Space Model",
        header_path=["Vector Space Model"],
        header_path_text="Vector Space Model",
        content_type="body",
        chunk_level="parent",
        retrieval_strategy="parent_child",
    )


def _retrieval_result(chunks: list[RetrievedChunk]) -> RetrievalResult:
    report = RetrievalReport(
        query="Vector Space Model là gì?",
        normalized_query="Vector Space Model là gì?",
        top_k=3,
        fetch_k=8,
        initial_results=len(chunks),
        after_threshold=len(chunks),
        after_dedup=len(chunks),
        final_results=len(chunks),
        min_score=0.9,
        max_score=0.9,
        avg_score=0.9,
        retrieval_time=0.01,
        embedding_time=0.001,
        vector_search_time=0.001,
        strategy="parent_child",
    )
    return RetrievalResult(
        query=report.query,
        normalized_query=report.normalized_query,
        context=RetrievedContext(query=report.query, normalized_query=report.normalized_query, strategy="parent_child", chunks=chunks),
        chunks=chunks,
        report=report,
    )

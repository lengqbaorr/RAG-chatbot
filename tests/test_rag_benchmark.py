from __future__ import annotations

from app.services.benchmark.models import BenchmarkCase
from app.cli.rag_benchmark import _slice_cases
from app.services.rag.models import Citation, RAGAnswer, RAGReport
from app.services.rag_benchmark import RAGBenchmarkConfig, RAGBenchmarkRunner, evaluate_rag_answer, summarize_rag_results
from app.services.retrieval.models import RetrievalReport


def test_rag_benchmark_scores_answer_keywords_and_source() -> None:
    case = BenchmarkCase(
        id="q1",
        question="Vector Space Model là gì?",
        expected_source_name="Test.pdf",
        expected_keywords=["vector", "truy xuất thông tin"],
    )
    config = RAGBenchmarkConfig(strategy="parent_child", min_score=0.76)

    result = evaluate_rag_answer(case, _answer("Vector dùng trong truy xuất thông tin."), config=config)

    assert result.failure_type is None
    assert result.answer_keyword_coverage == 1.0
    assert result.source_hit is True


def test_rag_benchmark_detects_unanswerable_refusal() -> None:
    case = BenchmarkCase(
        id="q2",
        question="Tài liệu có nói về blockchain không?",
        answerable=False,
    )
    config = RAGBenchmarkConfig()

    result = evaluate_rag_answer(
        case,
        _answer("Tôi không tìm thấy thông tin này trong tài liệu được cung cấp.", sources=[]),
        config=config,
    )
    report = summarize_rag_results([result], config=config)

    assert result.failure_type is None
    assert result.refused is True
    assert report.unanswerable_rejection == 1.0


def test_rag_benchmark_detects_keyword_miss() -> None:
    case = BenchmarkCase(
        id="q3",
        question="Vector Space Model là gì?",
        expected_source_name="Test.pdf",
        expected_keywords=["cosine similarity", "TFIDF"],
    )
    config = RAGBenchmarkConfig(min_answer_keyword_coverage=0.5)

    result = evaluate_rag_answer(case, _answer("Vector Space Model biểu diễn tài liệu thành vector."), config=config)

    assert result.failure_type == "answer_keyword_miss"


def test_rag_benchmark_records_llm_error_without_stopping() -> None:
    case = BenchmarkCase(id="q4", question="Test?", expected_keywords=["x"])
    runner = RAGBenchmarkRunner(_FailingPipeline())

    report = runner.run([case], [RAGBenchmarkConfig()])[0]

    assert len(report.failed_cases) == 1
    assert report.failed_cases[0].failure_type == "llm_error"


def test_rag_benchmark_slice_cases_with_offset_and_limit() -> None:
    cases = [
        BenchmarkCase(id=f"q{index}", question=f"Question {index}", expected_keywords=["x"])
        for index in range(5)
    ]

    selected = _slice_cases(cases, offset=1, limit=3)

    assert [case.id for case in selected] == ["q1", "q2", "q3"]


def _answer(text: str, *, sources: list[Citation] | None = None) -> RAGAnswer:
    retrieval_report = RetrievalReport(
        query="q",
        normalized_query="q",
        top_k=3,
        fetch_k=8,
        initial_results=1,
        after_threshold=1,
        after_dedup=1,
        final_results=1,
        min_score=0.9,
        max_score=0.9,
        avg_score=0.9,
        retrieval_time=0.01,
        embedding_time=0.001,
        vector_search_time=0.001,
        strategy="parent_child",
    )
    citations = sources
    if citations is None:
        citations = [
            Citation(
                source_number=1,
                source_id="src-1",
                source_name="Test.pdf",
                page_start=24,
                page_end=24,
                section_title="Vector Space Model",
                chunk_id="chunk-1",
                score=0.9,
                content_preview="Vector Space Model",
            )
        ]
    report = RAGReport(
        retrieval_report=retrieval_report,
        context_tokens=100,
        context_sources=len(citations),
        llm_provider="mock",
        llm_model="mock",
        llm_latency=0.02,
        total_latency=0.03,
    )
    return RAGAnswer(
        answer=text,
        sources=citations,
        retrieval_report=retrieval_report,
        llm_provider="mock",
        llm_model="mock",
        latency=0.03,
        report=report,
    )


class _FailingPipeline:
    def answer(self, *args, **kwargs):
        raise RuntimeError("quota exceeded")

from __future__ import annotations

import re
from statistics import mean

from app.services.benchmark.models import BenchmarkCase
from app.services.rag.models import Citation, RAGAnswer
from app.services.rag_benchmark.models import (
    RAGBenchmarkConfig,
    RAGBenchmarkReport,
    RAGBenchmarkResult,
)


def evaluate_rag_answer(
    case: BenchmarkCase,
    answer: RAGAnswer,
    *,
    config: RAGBenchmarkConfig,
) -> RAGBenchmarkResult:
    refused = _is_refusal(answer.answer, config.empty_answer_text)
    coverage = _keyword_coverage(case.expected_keywords, answer.answer)
    source_hit = _source_hit(case, answer.sources)
    citation_accuracy = 1.0 if source_hit else 0.0
    answered = not refused and bool(_normalize(answer.answer))

    failure_type = _classify_failure(
        case=case,
        refused=refused,
        answered=answered,
        keyword_coverage=coverage,
        source_hit=source_hit,
        min_keyword_coverage=config.min_answer_keyword_coverage,
    )

    return RAGBenchmarkResult(
        case_id=case.id,
        question=case.question,
        answerable=case.answerable,
        topic=case.topic,
        group=case.group,
        strategy=config.strategy,
        answered=answered,
        refused=refused,
        answer_keyword_coverage=coverage,
        citation_accuracy=citation_accuracy,
        source_hit=source_hit,
        retrieval_results=answer.retrieval_report.final_results,
        context_sources=answer.report.context_sources,
        retrieval_latency=answer.retrieval_report.retrieval_time,
        llm_latency=answer.report.llm_latency,
        total_latency=answer.report.total_latency,
        llm_provider=answer.llm_provider,
        llm_model=answer.llm_model,
        answer_preview=_preview(answer.answer),
        source_names=[source.source_name for source in answer.sources],
        source_pages=[_page_label(source) for source in answer.sources],
        failure_type=failure_type,
    )


def summarize_rag_results(
    results: list[RAGBenchmarkResult],
    *,
    config: RAGBenchmarkConfig,
) -> RAGBenchmarkReport:
    answerable = [result for result in results if result.answerable]
    unanswerable = [result for result in results if not result.answerable]
    failed = [result for result in results if result.failure_type]

    return RAGBenchmarkReport(
        config=config,
        total_questions=len(results),
        answerable_questions=len(answerable),
        unanswerable_questions=len(unanswerable),
        answer_accuracy=_avg([1.0 if not result.failure_type else 0.0 for result in answerable]),
        answer_keyword_coverage=_avg([result.answer_keyword_coverage for result in answerable]),
        citation_accuracy=_avg([result.citation_accuracy for result in answerable]),
        source_hit_rate=_avg([1.0 if result.source_hit else 0.0 for result in answerable]),
        unanswerable_rejection=_avg([1.0 if result.refused else 0.0 for result in unanswerable]),
        avg_retrieval_latency=_avg([result.retrieval_latency for result in results]),
        avg_llm_latency=_avg([result.llm_latency for result in results]),
        avg_total_latency=_avg([result.total_latency for result in results]),
        failed_cases=failed,
        results=results,
    )


def _classify_failure(
    *,
    case: BenchmarkCase,
    refused: bool,
    answered: bool,
    keyword_coverage: float,
    source_hit: bool,
    min_keyword_coverage: float,
) -> str | None:
    if not case.answerable:
        return None if refused else "unanswerable_not_rejected"
    if refused:
        return "answerable_refused"
    if not answered:
        return "empty_answer"
    if case.expected_source_name and not source_hit:
        return "wrong_or_missing_source"
    if case.expected_keywords and keyword_coverage < min_keyword_coverage:
        return "answer_keyword_miss"
    return None


def _keyword_coverage(keywords: list[str], text: str) -> float:
    if not keywords:
        return 1.0
    normalized_text = _normalize(text)
    hits = sum(1 for keyword in keywords if _normalize(keyword) in normalized_text)
    return hits / len(keywords)


def _source_hit(case: BenchmarkCase, sources: list[Citation]) -> bool:
    if not case.expected_source_name:
        return False
    expected = _normalize(case.expected_source_name)
    return any(_normalize(source.source_name) == expected for source in sources)


def _is_refusal(answer: str, empty_answer_text: str) -> bool:
    normalized_answer = _normalize(answer)
    normalized_empty = _normalize(empty_answer_text)
    if not normalized_answer:
        return True
    if normalized_empty and normalized_empty in normalized_answer:
        return True
    refusal_markers = (
        "không tìm thấy",
        "không có thông tin",
        "context không đủ",
        "tài liệu được cung cấp không",
    )
    return any(marker in normalized_answer for marker in refusal_markers)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _preview(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 3].rstrip() + "..."


def _page_label(source: Citation) -> str:
    if source.page_start is None and source.page_end is None:
        return ""
    if source.page_start == source.page_end or source.page_end is None:
        return str(source.page_start)
    if source.page_start is None:
        return str(source.page_end)
    return f"{source.page_start}-{source.page_end}"


def _avg(values: list[float]) -> float:
    return mean(values) if values else 0.0

from __future__ import annotations

import re
from statistics import mean

from app.services.benchmark.models import (
    BenchmarkCase,
    BenchmarkConfig,
    BenchmarkReport,
    BenchmarkResult,
    RelevanceScore,
)
from app.services.retrieval.models import RetrievedChunk, RetrievalResult


RELEVANCE_THRESHOLD = 0.5


def evaluate_retrieval_case(
    case: BenchmarkCase,
    retrieval_result: RetrievalResult,
    *,
    config: BenchmarkConfig,
) -> BenchmarkResult:
    chunks = retrieval_result.chunks[: config.top_k]
    scores = [
        score_chunk_relevance(case, chunk, page_tolerance=config.page_tolerance)
        for chunk in chunks
    ]
    relevant_indexes = [index for index, score in enumerate(scores, start=1) if score.relevant]
    hit_rank = relevant_indexes[0] if relevant_indexes else None
    reciprocal_rank = 1.0 / hit_rank if hit_rank else 0.0
    relevant_count = len(relevant_indexes)
    precision_at_k = relevant_count / config.top_k
    recall_at_k = 1.0 if hit_rank else 0.0

    keyword_coverage = _context_keyword_coverage(case, chunks)
    citation_accuracy = 1.0 if hit_rank else 0.0
    if not case.answerable:
        recall_at_k = 1.0 if not chunks else 0.0
        precision_at_k = 1.0 if not chunks else 0.0
        citation_accuracy = 1.0 if not chunks else 0.0
        reciprocal_rank = 1.0 if not chunks else 0.0

    return BenchmarkResult(
        case_id=case.id,
        question=case.question,
        answerable=case.answerable,
        topic=case.topic,
        group=case.group,
        strategy=config.strategy,
        hit_rank=hit_rank,
        reciprocal_rank=reciprocal_rank,
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        citation_accuracy=citation_accuracy,
        keyword_coverage=keyword_coverage,
        latency=retrieval_result.report.retrieval_time,
        top_scores=[chunk.score for chunk in chunks],
        retrieved_sources=[chunk.source_name for chunk in chunks],
        retrieved_pages=[_page_label(chunk) for chunk in chunks],
        retrieved_sections=[chunk.section_title or chunk.header_path_text for chunk in chunks],
        failure_type=_classify_failure(case, chunks, scores),
    )


def score_chunk_relevance(
    case: BenchmarkCase,
    chunk: RetrievedChunk,
    *,
    page_tolerance: int = 1,
) -> RelevanceScore:
    if not case.answerable:
        return RelevanceScore()

    source_match = _source_matches(case, chunk)
    page_match = _page_match_score(case, chunk, page_tolerance=page_tolerance)
    section_match = _section_match_score(case, chunk)
    keyword_match = _keyword_match_score(case, chunk.content)

    source_page_relevant = source_match and page_match > 0
    final_score = max(
        1.0 if source_page_relevant else 0.0,
        section_match,
        keyword_match,
    )
    return RelevanceScore(
        page_match_score=page_match,
        section_match_score=section_match,
        keyword_match_score=keyword_match,
        source_match=source_match,
        final_relevance_score=final_score,
        relevant=final_score >= RELEVANCE_THRESHOLD,
    )


def summarize_results(
    results: list[BenchmarkResult],
    *,
    config: BenchmarkConfig,
) -> BenchmarkReport:
    answerable = [result for result in results if result.answerable]
    unanswerable = [result for result in results if not result.answerable]
    failed = [result for result in results if result.failure_type]

    return BenchmarkReport(
        config=config,
        total_questions=len(results),
        answerable_questions=len(answerable),
        unanswerable_questions=len(unanswerable),
        recall_at_1=_recall_at(answerable, 1),
        recall_at_3=_recall_at(answerable, 3),
        recall_at_5=_recall_at(answerable, 5),
        recall_at_10=_recall_at(answerable, 10),
        precision_at_k=_avg([result.precision_at_k for result in answerable]),
        mrr=_avg([result.reciprocal_rank for result in answerable]),
        hit_rate=_avg([1.0 if result.hit_rank else 0.0 for result in answerable]),
        citation_accuracy=_avg([result.citation_accuracy for result in answerable]),
        keyword_coverage=_avg([result.keyword_coverage for result in answerable]),
        avg_latency=_avg([result.latency for result in results]),
        unanswerable_rejection=_avg([result.recall_at_k for result in unanswerable]),
        failed_cases=failed,
        results=results,
    )


def _source_matches(case: BenchmarkCase, chunk: RetrievedChunk) -> bool:
    if not case.expected_source_name:
        return False
    return _normalize(case.expected_source_name) == _normalize(chunk.source_name)


def _page_match_score(
    case: BenchmarkCase,
    chunk: RetrievedChunk,
    *,
    page_tolerance: int,
) -> float:
    if not case.expected_pages:
        return 0.0
    if chunk.page_start is None and chunk.page_end is None:
        return 0.0
    start = chunk.page_start or chunk.page_end or 0
    end = chunk.page_end or chunk.page_start or start
    retrieved_pages = set(range(max(1, start - page_tolerance), end + page_tolerance + 1))
    expected_pages = set(case.expected_pages)
    return 1.0 if retrieved_pages.intersection(expected_pages) else 0.0


def _section_match_score(case: BenchmarkCase, chunk: RetrievedChunk) -> float:
    if not case.expected_section:
        return 0.0
    expected = _normalize(case.expected_section)
    actual = _normalize(" ".join([chunk.section_title or "", chunk.header_path_text or ""]))
    if not expected or not actual:
        return 0.0
    if expected in actual or actual in expected:
        return 1.0
    for term in _section_terms(case.expected_section):
        normalized_term = _normalize(term)
        if normalized_term and normalized_term in actual:
            return 1.0
    return 0.0


def _keyword_match_score(case: BenchmarkCase, text: str) -> float:
    if not case.expected_keywords:
        return 0.0
    normalized_text = _normalize(text)
    hits = sum(1 for keyword in case.expected_keywords if _normalize(keyword) in normalized_text)
    return hits / len(case.expected_keywords)


def _context_keyword_coverage(case: BenchmarkCase, chunks: list[RetrievedChunk]) -> float:
    if not case.expected_keywords:
        return 1.0 if not case.answerable else 0.0
    combined = " ".join(chunk.content for chunk in chunks)
    return _keyword_match_score(case, combined)


def _classify_failure(
    case: BenchmarkCase,
    chunks: list[RetrievedChunk],
    scores: list[RelevanceScore],
) -> str | None:
    if not case.answerable:
        return None if not chunks else "unanswerable_not_rejected"
    if any(score.relevant for score in scores):
        return None
    if not chunks:
        return "low_score_or_empty"
    if case.expected_source_name and all(not _source_matches(case, chunk) for chunk in chunks):
        return "wrong_document"
    if case.expected_section and all(score.section_match_score == 0 for score in scores):
        return "wrong_section"
    if case.expected_keywords and max((score.keyword_match_score for score in scores), default=0.0) < RELEVANCE_THRESHOLD:
        return "keyword_miss"
    return "not_relevant"


def _recall_at(results: list[BenchmarkResult], k: int) -> float:
    return _avg([1.0 if result.hit_rank is not None and result.hit_rank <= k else 0.0 for result in results])


def _avg(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _section_terms(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[/|>]", text) if part.strip()]


def _page_label(chunk: RetrievedChunk) -> str:
    if chunk.page_start is None and chunk.page_end is None:
        return ""
    if chunk.page_start == chunk.page_end or chunk.page_end is None:
        return str(chunk.page_start)
    if chunk.page_start is None:
        return str(chunk.page_end)
    return f"{chunk.page_start}-{chunk.page_end}"

from __future__ import annotations

import re

from app.services.evaluation.config import EvaluationConfig
from app.services.evaluation.models import EvaluationCase, RelevanceScore
from app.services.retrieval.models import RetrievedChunk


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().casefold()


class RelevanceMatcher:
    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self.config = config or EvaluationConfig()

    def score(self, case: EvaluationCase, chunk: RetrievedChunk, *, rank: int) -> RelevanceScore:
        page_score = self.page_match_score(case, chunk)
        section_score = self.section_match_score(case, chunk)
        keyword_score = self.keyword_match_score(case, chunk)
        final_score = max(page_score, section_score, keyword_score)
        return RelevanceScore(
            chunk_id=chunk.chunk_id,
            rank=rank,
            page_match_score=round(page_score, 4),
            section_match_score=round(section_score, 4),
            keyword_match_score=round(keyword_score, 4),
            final_relevance_score=round(final_score, 4),
            is_relevant=final_score >= self.config.relevance_threshold,
        )

    def page_match_score(self, case: EvaluationCase, chunk: RetrievedChunk) -> float:
        expected_sources = self._expected_sources(case)
        if not expected_sources:
            return 0.0
        if normalize_text(chunk.source_name) not in expected_sources:
            return 0.0
        if not case.expected_pages:
            return 1.0
        if chunk.page_start is None or chunk.page_end is None:
            return 0.0
        retrieved_pages = set(range(chunk.page_start, chunk.page_end + 1))
        expected_pages = set(case.expected_pages)
        overlap = len(retrieved_pages & expected_pages)
        return overlap / max(1, len(expected_pages))

    def _expected_sources(self, case: EvaluationCase) -> set[str]:
        sources = set()
        if case.expected_source_name:
            sources.add(normalize_text(case.expected_source_name))
        sources.update(normalize_text(source) for source in case.expected_source_names)
        return {source for source in sources if source}

    def section_match_score(self, case: EvaluationCase, chunk: RetrievedChunk) -> float:
        if not case.expected_section:
            return 0.0
        expected = normalize_text(case.expected_section)
        haystack = normalize_text(
            " ".join([chunk.section_title or "", chunk.header_path_text or "", " ".join(chunk.header_path)])
        )
        if not expected or not haystack:
            return 0.0
        if expected in haystack:
            return 1.0
        expected_terms = set(re.findall(r"[\wÀ-ỹ]+", expected, flags=re.UNICODE))
        haystack_terms = set(re.findall(r"[\wÀ-ỹ]+", haystack, flags=re.UNICODE))
        if not expected_terms:
            return 0.0
        return len(expected_terms & haystack_terms) / len(expected_terms)

    def keyword_match_score(self, case: EvaluationCase, chunk: RetrievedChunk) -> float:
        if not case.expected_keywords:
            return 0.0
        text = normalize_text(chunk.content)
        matches = sum(1 for keyword in case.expected_keywords if normalize_text(keyword) in text)
        return matches / len(case.expected_keywords)


def recall_at_k(scores: list[RelevanceScore], k: int) -> float:
    return 1.0 if any(score.is_relevant for score in scores[:k]) else 0.0


def hit_rate_at_k(scores: list[RelevanceScore], k: int) -> bool:
    return bool(recall_at_k(scores, k))


def precision_at_k(scores: list[RelevanceScore], k: int) -> float:
    if k <= 0:
        return 0.0
    top_k = scores[:k]
    if not top_k:
        return 0.0
    return sum(1 for score in top_k if score.is_relevant) / k


def reciprocal_rank(scores: list[RelevanceScore]) -> float:
    for score in scores:
        if score.is_relevant:
            return 1.0 / score.rank
    return 0.0


def citation_accuracy(scores: list[RelevanceScore], k: int) -> float:
    top_k = scores[:k]
    if not top_k:
        return 0.0
    return 1.0 if any(
        score.page_match_score >= 1.0 or score.section_match_score >= 1.0 for score in top_k
    ) else 0.0


def keyword_coverage(scores: list[RelevanceScore], k: int) -> float:
    top_k = scores[:k]
    if not top_k:
        return 0.0
    return max((score.keyword_match_score for score in top_k), default=0.0)

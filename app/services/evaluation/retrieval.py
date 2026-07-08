from __future__ import annotations

import re
from collections import Counter

from pydantic import BaseModel, Field

from app.schemas.chunk import DocumentChunk


class EvaluationQuestion(BaseModel):
    question: str
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_pages: list[int] = Field(default_factory=list)
    expected_sections: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)


class RetrievedHit(BaseModel):
    chunk_id: str
    score: float
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    text: str = ""


class RetrievalEvaluationReport(BaseModel):
    total_questions: int
    k: int
    recall_at_k: float = 0.0
    mrr: float = 0.0
    citation_accuracy: float = 0.0
    unanswered_questions: int = 0


class RetrievalEvaluator:
    def evaluate(
        self,
        questions: list[EvaluationQuestion],
        results: list[list[RetrievedHit]],
        *,
        k: int = 5,
    ) -> RetrievalEvaluationReport:
        if len(questions) != len(results):
            raise ValueError("questions and results must have the same length")
        if not questions:
            return RetrievalEvaluationReport(total_questions=0, k=k)

        hits = 0
        reciprocal_ranks: list[float] = []
        citation_hits = 0
        unanswered = 0

        for question, question_results in zip(questions, results, strict=True):
            top_k = question_results[:k]
            if not top_k:
                unanswered += 1
                reciprocal_ranks.append(0.0)
                continue

            first_relevant_rank = self._first_relevant_rank(question, top_k)
            if first_relevant_rank is not None:
                hits += 1
                reciprocal_ranks.append(1 / first_relevant_rank)
            else:
                reciprocal_ranks.append(0.0)

            if any(self._citation_matches(question, hit) for hit in top_k):
                citation_hits += 1

        total = len(questions)
        return RetrievalEvaluationReport(
            total_questions=total,
            k=k,
            recall_at_k=round(hits / total, 4),
            mrr=round(sum(reciprocal_ranks) / total, 4),
            citation_accuracy=round(citation_hits / total, 4),
            unanswered_questions=unanswered,
        )

    def _first_relevant_rank(
        self,
        question: EvaluationQuestion,
        hits: list[RetrievedHit],
    ) -> int | None:
        for rank, hit in enumerate(hits, start=1):
            if self._is_relevant(question, hit):
                return rank
        return None

    def _is_relevant(self, question: EvaluationQuestion, hit: RetrievedHit) -> bool:
        if question.expected_chunk_ids and hit.chunk_id in question.expected_chunk_ids:
            return True
        if self._citation_matches(question, hit):
            return True
        if question.expected_keywords:
            text = hit.text.casefold()
            return all(keyword.casefold() in text for keyword in question.expected_keywords)
        return False

    def _citation_matches(self, question: EvaluationQuestion, hit: RetrievedHit) -> bool:
        if question.expected_pages and self._page_overlaps(question.expected_pages, hit):
            return True
        if question.expected_sections and hit.section_title:
            section = hit.section_title.casefold()
            return any(expected.casefold() in section for expected in question.expected_sections)
        return False

    def _page_overlaps(self, expected_pages: list[int], hit: RetrievedHit) -> bool:
        if hit.page_start is None or hit.page_end is None:
            return False
        hit_pages = set(range(hit.page_start, hit.page_end + 1))
        return any(page in hit_pages for page in expected_pages)


class LexicalChunkRetriever:
    def retrieve(
        self,
        question: str,
        chunks: list[DocumentChunk],
        *,
        k: int = 5,
        include_retrieval_excluded: bool = False,
    ) -> list[RetrievedHit]:
        query_terms = self._terms(question)
        if not query_terms:
            return []

        query_counts = Counter(query_terms)
        hits: list[RetrievedHit] = []
        for chunk in chunks:
            if chunk.metadata.chunk_level != "child":
                continue
            if chunk.metadata.retrieval_excluded and not include_retrieval_excluded:
                continue

            score = self._score(query_counts, self._terms(chunk.text))
            if score <= 0:
                continue

            hits.append(
                RetrievedHit(
                    chunk_id=chunk.chunk_id,
                    score=score,
                    page_start=chunk.metadata.page_start,
                    page_end=chunk.metadata.page_end,
                    section_title=chunk.metadata.section_title,
                    text=chunk.text,
                )
            )

        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:k]

    def _score(self, query_counts: Counter[str], chunk_terms: list[str]) -> float:
        chunk_counts = Counter(chunk_terms)
        overlap = sum(min(count, chunk_counts[term]) for term, count in query_counts.items())
        if overlap == 0:
            return 0.0
        return overlap / (len(query_counts) ** 0.5 * max(1, len(chunk_counts)) ** 0.5)

    def _terms(self, text: str) -> list[str]:
        return [
            term.casefold()
            for term in re.findall(r"[\wÀ-ỹ]+", text, flags=re.UNICODE)
            if len(term) > 1
        ]

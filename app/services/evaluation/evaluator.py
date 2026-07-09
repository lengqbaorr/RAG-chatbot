from __future__ import annotations

import time
from collections.abc import Iterable

from app.services.evaluation.config import EvaluationConfig
from app.services.evaluation.metrics import (
    RelevanceMatcher,
    citation_accuracy,
    keyword_coverage,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.services.evaluation.models import (
    EvaluationCase,
    EvaluationReport,
    EvaluationSummary,
    QuestionEvaluationResult,
    RelevanceScore,
)
from app.services.retrieval.models import RetrievalResult


class RetrievalEvaluator:
    def __init__(
        self,
        retriever,
        *,
        config: EvaluationConfig | None = None,
        config_name: str = "retrieval_eval",
    ) -> None:
        self.retriever = retriever
        self.config = config or EvaluationConfig()
        self.config_name = config_name
        self.matcher = RelevanceMatcher(self.config)

    def evaluate(self, cases: Iterable[EvaluationCase]) -> EvaluationReport:
        results: list[QuestionEvaluationResult] = []
        for case in cases:
            results.append(self.evaluate_case(case))
        return EvaluationReport(
            config_name=self.config_name,
            summary=self._aggregate(results),
            results=results,
        )

    def evaluate_case(self, case: EvaluationCase) -> QuestionEvaluationResult:
        started = time.perf_counter()
        retrieval_result = self.retriever.retrieve(
            case.question,
            strategy=self.config.default_strategy,
            filters=self.config.filters,
            top_k=max(self.config.recall_ks + (self.config.precision_k,)),
            fetch_k=self.config.default_fetch_k,
            min_score=self.config.default_min_score,
        )
        latency = time.perf_counter() - started
        chunks = retrieval_result.chunks
        scores = [
            self.matcher.score(case, chunk, rank=index)
            for index, chunk in enumerate(chunks, start=1)
        ]
        first_rank = next((score.rank for score in scores if score.is_relevant), None)
        recall_by_k = {k: recall_at_k(scores, k) for k in self.config.recall_ks}
        hit_by_k = {k: bool(recall_by_k[k]) for k in self.config.recall_ks}
        top_score = max((chunk.score for chunk in chunks), default=0.0)

        unanswerable_rejected = None
        if not case.answerable:
            unanswerable_rejected = top_score < self.config.unanswerable_score_threshold

        result = QuestionEvaluationResult(
            case_id=case.id,
            question=case.question,
            answerable=case.answerable,
            retrieved_count=len(chunks),
            top_score=top_score,
            first_relevant_rank=first_rank,
            reciprocal_rank=reciprocal_rank(scores),
            precision_at_k=precision_at_k(scores, self.config.precision_k),
            recall_by_k=recall_by_k,
            hit_by_k=hit_by_k,
            citation_accuracy=citation_accuracy(scores, self.config.citation_k),
            keyword_coverage=keyword_coverage(scores, self.config.citation_k),
            unanswerable_rejected=unanswerable_rejected,
            latency=retrieval_result.report.retrieval_time or latency,
            relevance_scores=scores,
            retrieved_sections=[
                chunk.header_path_text or chunk.section_title or ""
                for chunk in chunks
            ],
            retrieved_scores=[chunk.score for chunk in chunks],
        )
        return result.model_copy(update={"failure_type": self._classify_failure(case, result, scores)})

    def _aggregate(self, results: list[QuestionEvaluationResult]) -> EvaluationSummary:
        total = len(results)
        answerable = [result for result in results if result.answerable]
        unanswerable = [result for result in results if not result.answerable]
        failed = [result for result in results if result.failure_type is not None]

        recall: dict[int, float] = {}
        for k in self.config.recall_ks:
            recall[k] = self._avg([result.recall_by_k.get(k, 0.0) for result in answerable])

        return EvaluationSummary(
            total_questions=total,
            answerable_questions=len(answerable),
            unanswerable_questions=len(unanswerable),
            recall_at_k=recall,
            mrr=self._avg([result.reciprocal_rank for result in answerable]),
            precision_at_k=self._avg([result.precision_at_k for result in answerable]),
            citation_accuracy=self._avg([result.citation_accuracy for result in answerable]),
            keyword_coverage=self._avg([result.keyword_coverage for result in answerable]),
            unanswerable_rejection=self._avg([
                1.0 if result.unanswerable_rejected else 0.0
                for result in unanswerable
            ]),
            avg_latency=self._avg([result.latency for result in results]),
            failed_cases=len(failed),
        )

    def _classify_failure(
        self,
        case: EvaluationCase,
        result: QuestionEvaluationResult,
        scores: list[RelevanceScore],
    ) -> str | None:
        if not case.answerable:
            return None if result.unanswerable_rejected else "semantic_confusion"
        if result.first_relevant_rank is not None:
            return None
        if result.retrieved_count == 0:
            return "missing_chunk"
        if result.top_score < self.config.default_min_score:
            return "threshold_too_high"
        if result.top_score < self.config.unanswerable_score_threshold:
            return "low_score"
        if case.expected_section and all(
            score.section_match_score < self.config.relevance_threshold for score in scores
        ):
            return "wrong_section"
        if case.expected_source_name and all(
            score.page_match_score < self.config.relevance_threshold for score in scores
        ):
            return "wrong_document"
        if case.expected_keywords and all(score.keyword_match_score == 0 for score in scores):
            return "bad_query"
        return "semantic_confusion"

    def _avg(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)

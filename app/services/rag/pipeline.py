from __future__ import annotations

from collections.abc import Iterator
import logging

from app.services.rag.answer_generator import AnswerGenerator
from app.services.rag.config import RAGPipelineConfig
from app.services.rag.models import RAGAnswer, RAGStreamEvent
from app.services.llm.models import LLMMessage
from app.services.reranking import RerankerService
from app.services.retrieval.models import RetrievalResult
from app.services.retrieval.service import RetrievalService


logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        *,
        retriever_service: RetrievalService,
        answer_generator: AnswerGenerator,
        reranker_service: RerankerService | None = None,
        config: RAGPipelineConfig | None = None,
    ) -> None:
        self.retriever_service = retriever_service
        self.answer_generator = answer_generator
        self.reranker_service = reranker_service
        self.config = config or RAGPipelineConfig()

    def answer(
        self,
        question: str,
        *,
        retrieval_query: str | None = None,
        conversation_history: list[LLMMessage] | None = None,
        strategy: str | None = None,
        filters: dict | None = None,
        top_k: int | None = None,
        fetch_k: int | None = None,
        min_score: float | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reranker_enabled: bool = False,
        reranker_model: str | None = None,
    ) -> RAGAnswer:
        final_top_k = top_k or self.config.top_k
        retrieval_result = self._retrieve_with_fallback(
            question=retrieval_query or question,
            strategy=strategy,
            filters=filters,
            top_k=final_top_k,
            fetch_k=fetch_k,
            min_score=min_score,
            reranker_enabled=reranker_enabled,
        )
        retrieval_result = self._maybe_rerank(
            question=retrieval_query or question,
            result=retrieval_result,
            top_k=final_top_k,
            enabled=reranker_enabled,
            model_name=reranker_model,
        )
        return self.answer_generator.generate(
            question=question,
            retrieval_result=retrieval_result,
            report_metadata=self._report_metadata(
                question=question,
                retrieval_query=retrieval_query,
            ),
            conversation_history=conversation_history,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def stream(
        self,
        question: str,
        *,
        retrieval_query: str | None = None,
        conversation_history: list[LLMMessage] | None = None,
        strategy: str | None = None,
        filters: dict | None = None,
        top_k: int | None = None,
        fetch_k: int | None = None,
        min_score: float | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reranker_enabled: bool = False,
        reranker_model: str | None = None,
    ) -> Iterator[RAGStreamEvent]:
        final_top_k = top_k or self.config.top_k
        retrieval_result = self._retrieve_with_fallback(
            question=retrieval_query or question,
            strategy=strategy,
            filters=filters,
            top_k=final_top_k,
            fetch_k=fetch_k,
            min_score=min_score,
            reranker_enabled=reranker_enabled,
        )
        retrieval_result = self._maybe_rerank(
            question=retrieval_query or question,
            result=retrieval_result,
            top_k=final_top_k,
            enabled=reranker_enabled,
            model_name=reranker_model,
        )
        yield from self.answer_generator.stream(
            question=question,
            retrieval_result=retrieval_result,
            report_metadata=self._report_metadata(
                question=question,
                retrieval_query=retrieval_query,
            ),
            conversation_history=conversation_history,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _maybe_rerank(
        self,
        *,
        question: str,
        result,
        top_k: int,
        enabled: bool,
        model_name: str | None,
    ):
        if not enabled or self.reranker_service is None:
            return result
        try:
            return self.reranker_service.rerank_result(
                query=question,
                result=result,
                top_k=top_k,
                model_name=model_name,
            )
        except Exception:
            logger.exception("reranker_failed_fallback_to_retrieval")
            return result

    def _retrieve_with_fallback(
        self,
        *,
        question: str,
        strategy: str | None,
        filters: dict | None,
        top_k: int,
        fetch_k: int | None,
        min_score: float | None,
        reranker_enabled: bool,
    ) -> RetrievalResult:
        effective_fetch_k = fetch_k or self.config.fetch_k
        effective_min_score = min_score if min_score is not None else self.config.min_score
        result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=effective_fetch_k if reranker_enabled else top_k,
            fetch_k=effective_fetch_k,
            min_score=effective_min_score,
        )
        if not self._should_retry_with_lower_score(result, effective_min_score):
            return result

        fallback_score = self.config.fallback_min_score
        logger.info(
            "empty_retrieval_retry_with_lower_score",
            extra={
                "original_min_score": effective_min_score,
                "fallback_min_score": fallback_score,
                "strategy": strategy or self.config.retrieval_strategy,
            },
        )
        fallback_result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=effective_fetch_k if reranker_enabled else top_k,
            fetch_k=effective_fetch_k,
            min_score=fallback_score,
        )
        if fallback_result.report.final_results == 0:
            return result
        report = fallback_result.report.model_copy(
            update={
                "strategy": f"{fallback_result.report.strategy}+fallback_{fallback_score:g}",
            }
        )
        context = fallback_result.context.model_copy(update={"strategy": report.strategy})
        return fallback_result.model_copy(update={"report": report, "context": context})

    def _should_retry_with_lower_score(
        self,
        result: RetrievalResult,
        min_score: float | None,
    ) -> bool:
        if not self.config.enable_empty_retrieval_fallback:
            return False
        if result.report.final_results > 0:
            return False
        if min_score is None:
            return False
        return min_score > self.config.fallback_min_score

    @staticmethod
    def _report_metadata(
        *,
        question: str,
        retrieval_query: str | None,
    ) -> dict:
        effective_query = retrieval_query or question
        return {
            "original_question": question,
            "retrieval_query": effective_query,
            "query_rewritten": effective_query.strip() != question.strip(),
        }

from __future__ import annotations

from collections.abc import Iterator
import logging

from app.services.rag.answer_generator import AnswerGenerator
from app.services.rag.config import RAGPipelineConfig
from app.services.rag.models import RAGAnswer, RAGStreamEvent
from app.services.reranking import RerankerService
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
        retrieval_result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=(fetch_k or self.config.fetch_k) if reranker_enabled else final_top_k,
            fetch_k=fetch_k or self.config.fetch_k,
            min_score=min_score if min_score is not None else self.config.min_score,
        )
        retrieval_result = self._maybe_rerank(
            question=question,
            result=retrieval_result,
            top_k=final_top_k,
            enabled=reranker_enabled,
            model_name=reranker_model,
        )
        return self.answer_generator.generate(
            question=question,
            retrieval_result=retrieval_result,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def stream(
        self,
        question: str,
        *,
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
        retrieval_result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=(fetch_k or self.config.fetch_k) if reranker_enabled else final_top_k,
            fetch_k=fetch_k or self.config.fetch_k,
            min_score=min_score if min_score is not None else self.config.min_score,
        )
        retrieval_result = self._maybe_rerank(
            question=question,
            result=retrieval_result,
            top_k=final_top_k,
            enabled=reranker_enabled,
            model_name=reranker_model,
        )
        yield from self.answer_generator.stream(
            question=question,
            retrieval_result=retrieval_result,
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

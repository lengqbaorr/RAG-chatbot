from __future__ import annotations

from collections.abc import Iterator

from app.services.rag.answer_generator import AnswerGenerator
from app.services.rag.config import RAGPipelineConfig
from app.services.rag.models import RAGAnswer, RAGStreamEvent
from app.services.retrieval.service import RetrievalService


class RAGPipeline:
    def __init__(
        self,
        *,
        retriever_service: RetrievalService,
        answer_generator: AnswerGenerator,
        config: RAGPipelineConfig | None = None,
    ) -> None:
        self.retriever_service = retriever_service
        self.answer_generator = answer_generator
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
    ) -> RAGAnswer:
        retrieval_result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=top_k or self.config.top_k,
            fetch_k=fetch_k or self.config.fetch_k,
            min_score=min_score if min_score is not None else self.config.min_score,
        )
        return self.answer_generator.generate(
            question=question,
            retrieval_result=retrieval_result,
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
    ) -> Iterator[RAGStreamEvent]:
        retrieval_result = self.retriever_service.retrieve(
            question,
            strategy=strategy or self.config.retrieval_strategy,
            filters=filters,
            top_k=top_k or self.config.top_k,
            fetch_k=fetch_k or self.config.fetch_k,
            min_score=min_score if min_score is not None else self.config.min_score,
        )
        yield from self.answer_generator.stream(
            question=question,
            retrieval_result=retrieval_result,
        )

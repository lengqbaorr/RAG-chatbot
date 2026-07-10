from __future__ import annotations

import time

from app.services.llm.service import LLMService
from app.services.rag.citation_builder import CitationBuilder
from app.services.rag.config import RAGPipelineConfig
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.models import RAGAnswer, RAGReport
from app.services.rag.prompt_builder import PromptBuilder
from app.services.retrieval.models import RetrievalResult


class AnswerGenerator:
    def __init__(
        self,
        *,
        llm_service: LLMService,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
        config: RAGPipelineConfig | None = None,
    ) -> None:
        self.llm_service = llm_service
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.citation_builder = citation_builder or CitationBuilder()
        self.config = config or RAGPipelineConfig()

    def generate(self, *, question: str, retrieval_result: RetrievalResult) -> RAGAnswer:
        started = time.perf_counter()
        context = self.context_builder.build(retrieval_result)
        citations = self.citation_builder.build(context)

        if not context.sources and not self.config.call_llm_on_empty_context:
            latency = time.perf_counter() - started
            report = RAGReport(
                retrieval_report=retrieval_result.report,
                context_tokens=0,
                context_sources=0,
                context_truncated=False,
                total_latency=latency,
            )
            return RAGAnswer(
                answer=self.config.empty_context_answer,
                sources=[],
                retrieval_report=retrieval_result.report,
                latency=latency,
                report=report,
            )

        request = self.prompt_builder.build(question=question, context=context)
        response = self.llm_service.generate(request)
        latency = time.perf_counter() - started
        report = RAGReport(
            retrieval_report=retrieval_result.report,
            context_tokens=context.token_count,
            context_sources=len(context.sources),
            context_truncated=context.truncated,
            llm_provider=response.provider,
            llm_model=response.model,
            llm_latency=response.latency,
            llm_finish_reason=response.finish_reason,
            llm_prompt_tokens=response.usage.prompt_tokens,
            llm_completion_tokens=response.usage.completion_tokens,
            llm_total_tokens=response.usage.total_tokens,
            total_latency=latency,
        )
        return RAGAnswer(
            answer=response.text,
            sources=citations,
            retrieval_report=retrieval_result.report,
            llm_provider=response.provider,
            llm_model=response.model,
            latency=latency,
            usage=response.usage,
            report=report,
        )

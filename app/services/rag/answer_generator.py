from __future__ import annotations

import re
import time
from collections.abc import Iterator

from app.services.llm.service import LLMService
from app.services.rag.citation_builder import CitationBuilder
from app.services.rag.config import RAGPipelineConfig
from app.services.rag.context_builder import ContextBuilder
from app.services.llm.models import LLMUsage
from app.services.rag.models import RAGAnswer, RAGReport, RAGStreamEvent
from app.services.rag.prompt_builder import PromptBuilder
from app.services.retrieval.models import RetrievalResult


INLINE_SOURCE_PATTERN = re.compile(r"\s*\[\s*Source\s+\d+\s*\]", re.IGNORECASE)


def strip_inline_sources(text: str) -> str:
    cleaned = INLINE_SOURCE_PATTERN.sub("", text)
    return re.sub(r"\s+([.,;:!?])", r"\1", cleaned).strip()


class _StreamingSourceMarkerFilter:
    def __init__(self) -> None:
        self._buffer = ""

    def push(self, text: str) -> str:
        combined = INLINE_SOURCE_PATTERN.sub("", self._buffer + text)
        self._buffer = ""
        opening = combined.rfind("[")
        if opening >= 0 and "]" not in combined[opening:] and len(combined) - opening < 32:
            self._buffer = combined[opening:]
            combined = combined[:opening]
        elif combined and combined[-1].isspace():
            stripped = combined.rstrip()
            self._buffer = combined[len(stripped):]
            combined = stripped
        return combined

    def finish(self) -> str:
        remaining = INLINE_SOURCE_PATTERN.sub("", self._buffer)
        self._buffer = ""
        return remaining


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
            answer=strip_inline_sources(response.text),
            sources=citations,
            retrieval_report=retrieval_result.report,
            llm_provider=response.provider,
            llm_model=response.model,
            latency=latency,
            usage=response.usage,
            report=report,
        )

    def stream(
        self,
        *,
        question: str,
        retrieval_result: RetrievalResult,
    ) -> Iterator[RAGStreamEvent]:
        started = time.perf_counter()
        context = self.context_builder.build(retrieval_result)
        citations = self.citation_builder.build(context)
        yield RAGStreamEvent(event="start")

        if not context.sources and not self.config.call_llm_on_empty_context:
            latency = time.perf_counter() - started
            report = RAGReport(
                retrieval_report=retrieval_result.report,
                context_tokens=0,
                context_sources=0,
                context_truncated=False,
                total_latency=latency,
            )
            yield RAGStreamEvent(
                event="complete",
                answer=RAGAnswer(
                    answer=self.config.empty_context_answer,
                    sources=[],
                    retrieval_report=retrieval_result.report,
                    latency=latency,
                    report=report,
                ),
            )
            return

        request = self.prompt_builder.build(question=question, context=context)
        answer_parts: list[str] = []
        provider: str | None = None
        model: str | None = None
        finish_reason: str | None = None
        usage = LLMUsage()
        source_filter = _StreamingSourceMarkerFilter()
        llm_started = time.perf_counter()
        stream = self.llm_service.stream(request)
        try:
            for chunk in stream:
                provider = chunk.provider
                model = chunk.model
                finish_reason = chunk.finish_reason or finish_reason
                if any(
                    value is not None
                    for value in (
                        chunk.usage.prompt_tokens,
                        chunk.usage.completion_tokens,
                        chunk.usage.total_tokens,
                    )
                ):
                    usage = chunk.usage
                if chunk.text:
                    visible_text = source_filter.push(chunk.text)
                    if visible_text:
                        answer_parts.append(visible_text)
                        yield RAGStreamEvent(event="delta", text=visible_text)
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                close()

        remaining_text = source_filter.finish()
        if remaining_text:
            answer_parts.append(remaining_text)
            yield RAGStreamEvent(event="delta", text=remaining_text)
        llm_latency = time.perf_counter() - llm_started
        latency = time.perf_counter() - started
        report = RAGReport(
            retrieval_report=retrieval_result.report,
            context_tokens=context.token_count,
            context_sources=len(context.sources),
            context_truncated=context.truncated,
            llm_provider=provider,
            llm_model=model,
            llm_latency=llm_latency,
            llm_finish_reason=finish_reason,
            llm_prompt_tokens=usage.prompt_tokens,
            llm_completion_tokens=usage.completion_tokens,
            llm_total_tokens=usage.total_tokens,
            total_latency=latency,
        )
        yield RAGStreamEvent(
            event="complete",
            answer=RAGAnswer(
                answer=strip_inline_sources("".join(answer_parts)),
                sources=citations,
                retrieval_report=retrieval_result.report,
                llm_provider=provider,
                llm_model=model,
                latency=latency,
                usage=usage,
                report=report,
            ),
        )

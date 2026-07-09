from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMRequest,
    LLMResponse,
    LLMService,
    LLMUsage,
)
from app.services.rag import AnswerGenerator, RAGPipeline, RAGPipelineConfig
from app.services.retrieval.models import (
    RetrievedChunk,
    RetrievedContext,
    RetrievalReport,
    RetrievalResult,
)


class MockLLMProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-rag-model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        del request
        return LLMResponse(
            text=(
                "Bông tuyết Koch được xây dựng bằng cách chia mỗi đoạn thẳng "
                "thành ba phần, dựng tam giác đều ở đoạn giữa, bỏ cạnh đáy, "
                "rồi lặp lại quy trình này đệ quy. [Source 1]"
            ),
            model=self.default_model,
            provider=self.provider_name,
            usage=LLMUsage(prompt_tokens=120, completion_tokens=40, total_tokens=160),
            latency=0.01,
            finish_reason="stop",
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        del request
        yield "Bông tuyết Koch được xây dựng bằng quy trình đệ quy. [Source 1]"


class MockRetrieverService:
    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        del kwargs
        chunk = RetrievedChunk(
            chunk_id="parent-koch",
            document_id="doc-fractal",
            source_id="src-fractal",
            content=(
                "Bông tuyết Koch được tạo bằng cách chia mỗi đoạn thẳng thành ba phần, "
                "dựng tam giác đều ở đoạn giữa, loại bỏ cạnh đáy và lặp lại đệ quy."
            ),
            metadata={"content_hash": "hash-parent-koch"},
            score=0.91,
            distance=0.09,
            rank=1,
            source_name="23520108_23520383_23521714.pdf",
            source_type="pdf",
            page_start=2,
            page_end=4,
            section_title="2.1. Bông tuyết Koch",
            header_path=["2.1. Bông tuyết Koch"],
            header_path_text="2.1. Bông tuyết Koch",
            content_type="body",
            chunk_level="parent",
            retrieval_strategy="parent_child",
        )
        report = RetrievalReport(
            query=query,
            normalized_query=query,
            top_k=3,
            fetch_k=10,
            initial_results=1,
            after_threshold=1,
            after_dedup=1,
            final_results=1,
            min_score=0.91,
            max_score=0.91,
            avg_score=0.91,
            retrieval_time=0.01,
            embedding_time=0.001,
            vector_search_time=0.002,
            strategy="parent_child",
        )
        return RetrievalResult(
            query=query,
            normalized_query=query,
            context=RetrievedContext(
                query=query,
                normalized_query=query,
                strategy="parent_child",
                chunks=[chunk],
            ),
            chunks=[chunk],
            report=report,
        )


def main() -> None:
    question = "Bông tuyết Koch được xây dựng như thế nào?"
    llm_service = LLMService(
        config=LLMConfig(provider="mock", model="mock-rag-model"),
        providers={"mock": MockLLMProvider()},
    )
    pipeline = RAGPipeline(
        retriever_service=MockRetrieverService(),
        answer_generator=AnswerGenerator(llm_service=llm_service),
        config=RAGPipelineConfig(retrieval_strategy="parent_child", top_k=3, fetch_k=10),
    )

    result = pipeline.answer(question)

    print("=" * 72)
    print("  DEMO: RAG Answer Pipeline (mock retriever + mock LLM)")
    print("=" * 72)
    print(f"\nquestion: {question}")
    print(f"\nanswer:   {result.answer}")
    print("\nsources:")
    for source in result.sources:
        print(f"  [{source.source_number}] {source.source_name} page {source.page_start}-{source.page_end}")
        print(f"      section: {source.section_title}")
        print(f"      score:   {source.score:.4f}")
    print("\nreport:")
    print(f"  strategy:        {result.retrieval_report.strategy}")
    print(f"  context_sources: {result.report.context_sources}")
    print(f"  llm:             {result.llm_provider}/{result.llm_model}")
    print(f"  total_latency:   {result.latency:.4f}s")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import sys
import argparse
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
                "Vector Space Model biểu diễn tài liệu và truy vấn thành các vector "
                "trong không gian nhiều chiều, sau đó đo độ tương đồng giữa chúng, "
                "thường bằng cosine similarity. [Source 1]"
            ),
            model=self.default_model,
            provider=self.provider_name,
            usage=LLMUsage(prompt_tokens=120, completion_tokens=40, total_tokens=160),
            latency=0.01,
            finish_reason="stop",
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        del request
        yield "Vector Space Model biểu diễn văn bản thành vector. [Source 1]"


class MockRetrieverService:
    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        del kwargs
        chunk = RetrievedChunk(
            chunk_id="parent-vsm",
            document_id="doc-vsm",
            source_id="src-vsm",
            content=(
                "Vector Space Model biểu diễn tài liệu và truy vấn dưới dạng vector. "
                "Mỗi chiều có thể là một thuật ngữ, trọng số có thể dựa trên TF-IDF, "
                "và độ tương đồng thường được tính bằng cosine similarity."
            ),
            metadata={"content_hash": "hash-parent-vsm"},
            score=0.91,
            distance=0.09,
            rank=1,
            source_name="Test.pdf",
            source_type="pdf",
            page_start=8,
            page_end=11,
            section_title="Vector Space Model",
            header_path=["Vector Space Model"],
            header_path_text="Vector Space Model",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo RAG Answer Pipeline with mock services.")
    parser.add_argument("--query", default="Vector Space Model là gì?")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    question = args.query
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


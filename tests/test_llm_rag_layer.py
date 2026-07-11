from __future__ import annotations

from collections.abc import Iterator

import pytest
import requests

from app.services.llm import (
    BaseLLMProvider,
    LLMConfig,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMService,
    LLMStreamChunk,
    LLMUsage,
)
from app.services.llm.providers.gemini_provider import GeminiProvider
from app.services.rag import (
    AnswerGenerator,
    CitationBuilder,
    ContextBuilder,
    ContextBuilderConfig,
    PromptBuilder,
    RAGPipeline,
    RAGPipelineConfig,
)
from app.services.retrieval.models import (
    RetrievedContext,
    RetrievedChunk,
    RetrievalReport,
    RetrievalResult,
)


class FakeLLMProvider(BaseLLMProvider):
    def __init__(self, *, provider_name: str = "fake", text: str = "Câu trả lời [Source 1].") -> None:
        self._provider_name = provider_name
        self.text = text
        self.requests: list[LLMRequest] = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def default_model(self) -> str:
        return "fake-model"

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            text=self.text,
            model=request.model or self.default_model,
            provider=self.provider_name,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            latency=0.01,
            finish_reason="stop",
        )

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamChunk]:
        self.requests.append(request)
        for text in ("Câu trả lời ", "[Source 1]."):
            yield LLMStreamChunk(
                text=text,
                model=request.model or self.default_model,
                provider=self.provider_name,
            )
        yield LLMStreamChunk(
            model=request.model or self.default_model,
            provider=self.provider_name,
            finish_reason="STOP",
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


class FakeRetrieverService:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def retrieve(self, query: str, **kwargs) -> RetrievalResult:
        self.calls.append({"query": query, **kwargs})
        return self.result


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("bad request")

    def json(self) -> dict:
        return self.payload


class FakeStreamingResponse(FakeResponse):
    def __init__(self, lines: list[str | bytes], status_code: int = 200) -> None:
        super().__init__({}, status_code=status_code)
        self.lines = lines
        self.closed = False

    def iter_lines(self, decode_unicode: bool = False):
        del decode_unicode
        yield from self.lines

    def close(self) -> None:
        self.closed = True


def _chunk(
    chunk_id: str,
    *,
    content: str = "Bông tuyết Koch được xây dựng bằng cách chia đoạn thẳng thành ba phần.",
    score: float = 0.9,
    page_start: int = 2,
    page_end: int = 2,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        source_id="src-1",
        content=content,
        metadata={"content_hash": f"hash-{chunk_id}"},
        score=score,
        distance=1.0 - score,
        rank=1,
        source_name="fractal.pdf",
        source_type="pdf",
        page_start=page_start,
        page_end=page_end,
        section_title="2.1. Bông tuyết Koch",
        header_path=["2.1. Bông tuyết Koch"],
        header_path_text="2.1. Bông tuyết Koch",
        content_type="body",
        chunk_level="parent",
        parent_id=None,
        retrieval_strategy="parent_child",
    )


def _retrieval_result(chunks: list[RetrievedChunk] | None = None) -> RetrievalResult:
    chunks = chunks or []
    report = RetrievalReport(
        query="Koch?",
        normalized_query="Koch?",
        top_k=5,
        fetch_k=20,
        initial_results=len(chunks),
        after_threshold=len(chunks),
        after_dedup=len(chunks),
        final_results=len(chunks),
        min_score=min((chunk.score for chunk in chunks), default=0.0),
        max_score=max((chunk.score for chunk in chunks), default=0.0),
        avg_score=sum(chunk.score for chunk in chunks) / len(chunks) if chunks else 0.0,
        retrieval_time=0.01,
        embedding_time=0.001,
        vector_search_time=0.002,
        strategy="parent_child",
    )
    return RetrievalResult(
        query="Koch?",
        normalized_query="Koch?",
        context=RetrievedContext(
            query="Koch?",
            normalized_query="Koch?",
            strategy="parent_child",
            chunks=chunks,
        ),
        chunks=chunks,
        report=report,
    )


def test_context_builder_limits_token_budget() -> None:
    chunks = [
        _chunk("c1", content=" ".join(["a"] * 20)),
        _chunk("c2", content=" ".join(["b"] * 20)),
    ]
    builder = ContextBuilder(config=ContextBuilderConfig(max_context_tokens=70))

    context = builder.build(_retrieval_result(chunks))

    assert len(context.sources) == 1
    assert context.truncated is True
    assert "[Source 1]" in context.text


def test_context_builder_truncates_first_oversized_block() -> None:
    chunk = _chunk("c1", content=" ".join(["long"] * 200))
    builder = ContextBuilder(config=ContextBuilderConfig(max_context_tokens=40))

    context = builder.build(_retrieval_result([chunk]))

    assert len(context.sources) == 1
    assert context.truncated is True
    assert context.token_count <= 40


def test_context_builder_keeps_source_metadata() -> None:
    context = ContextBuilder().build(_retrieval_result([_chunk("c1")]))

    assert context.sources[0].source_name == "fractal.pdf"
    assert context.sources[0].page_start == 2
    assert context.sources[0].section_title == "2.1. Bông tuyết Koch"


def test_prompt_builder_contains_required_rules_and_context() -> None:
    context = ContextBuilder().build(_retrieval_result([_chunk("c1")]))

    request = PromptBuilder().build(question="Koch xây dựng thế nào?", context=context)

    assert request.messages[0].role == "system"
    assert "Chỉ sử dụng thông tin trong CONTEXT" in request.messages[0].content
    assert "Không chèn ký hiệu [Source n]" in request.messages[0].content
    assert "QUESTION:" in request.messages[-1].content
    assert "[Source 1]" in request.messages[-1].content


def test_llm_service_routes_to_selected_provider() -> None:
    fake = FakeLLMProvider(provider_name="fake")
    service = LLMService(config=LLMConfig(provider="fake", model="fake-model"), providers={"fake": fake})

    response = service.generate(LLMRequest(messages=[LLMMessage(role="user", content="Hello")]))

    assert response.provider == "fake"
    assert fake.requests[0].model == "fake-model"


def test_gemini_provider_can_be_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": "Trả lời [Source 1]."}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 12,
            "candidatesTokenCount": 7,
            "totalTokenCount": 19,
        },
    }
    calls: list[dict] = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse(payload)

    monkeypatch.setattr("app.services.llm.providers.gemini_provider.requests.post", fake_post)
    provider = GeminiProvider(api_key="test-key", timeout_seconds=5)

    response = provider.generate(
        LLMRequest(
            messages=[
                LLMMessage(role="system", content="System"),
                LLMMessage(role="user", content="Question"),
            ],
            model="gemini-test",
            temperature=0.2,
            max_tokens=128,
        )
    )

    assert response.text == "Trả lời [Source 1]."
    assert response.usage.total_tokens == 19
    assert calls[0]["headers"] == {"x-goog-api-key": "test-key"}
    assert calls[0]["json"]["systemInstruction"]["parts"][0]["text"] == "System"


def test_gemini_provider_streams_text_and_final_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    response = FakeStreamingResponse(
        [
            'data: {"candidates":[{"content":{"parts":[{"text":"Xin chào, tiếng Việt: "}]}}]}'.encode("utf-8"),
            "",
            'data: {"candidates":[{"content":{"parts":[',
            '{"text":"chào',
            'bạn"}]},"finishReason":"STOP"}],',
            '"usageMetadata":{"promptTokenCount":3,"candidatesTokenCount":2,"totalTokenCount":5}}',
            "",
        ]
    )

    def fake_post(url, headers, json, timeout, stream):
        assert url.endswith(":streamGenerateContent?alt=sse")
        assert stream is True
        del headers, json, timeout
        return response

    monkeypatch.setattr("app.services.llm.providers.gemini_provider.requests.post", fake_post)
    provider = GeminiProvider(api_key="test-key")

    chunks = list(
        provider.stream(
            LLMRequest(messages=[LLMMessage(role="user", content="Hello")], model="gemini-test")
        )
    )

    assert "".join(chunk.text for chunk in chunks) == "Xin chào, tiếng Việt: chào\nbạn"
    assert chunks[-1].finish_reason == "STOP"
    assert chunks[-1].usage.total_tokens == 5
    assert response.closed is True


def test_gemini_provider_retries_transient_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "candidates": [{"content": {"parts": [{"text": "OK"}]}, "finishReason": "STOP"}],
    }
    calls = {"count": 0}

    def fake_post(url, headers, json, timeout):
        del url, headers, json, timeout
        calls["count"] += 1
        if calls["count"] == 1:
            return FakeResponse({"error": {"code": 503}}, status_code=503)
        return FakeResponse(payload)

    monkeypatch.setattr("app.services.llm.providers.gemini_provider.requests.post", fake_post)
    monkeypatch.setattr("app.services.llm.providers.gemini_provider.wait_exponential", lambda **kwargs: None)
    provider = GeminiProvider(api_key="test-key", timeout_seconds=5)

    response = provider.generate(
        LLMRequest(messages=[LLMMessage(role="user", content="Question")], model="gemini-test")
    )

    assert response.text == "OK"
    assert calls["count"] == 2


def test_citation_builder_creates_citations() -> None:
    context = ContextBuilder().build(_retrieval_result([_chunk("c1")]))

    citations = CitationBuilder().build(context)

    assert citations[0].source_number == 1
    assert citations[0].source_name == "fractal.pdf"
    assert citations[0].chunk_id == "c1"


def test_rag_pipeline_with_mock_retriever_and_llm() -> None:
    retrieval_result = _retrieval_result([_chunk("c1")])
    retriever = FakeRetrieverService(retrieval_result)
    provider = FakeLLMProvider()
    llm_service = LLMService(config=LLMConfig(provider="fake"), providers={"fake": provider})
    answer_generator = AnswerGenerator(llm_service=llm_service)
    pipeline = RAGPipeline(
        retriever_service=retriever,
        answer_generator=answer_generator,
        config=RAGPipelineConfig(retrieval_strategy="parent_child", top_k=3, fetch_k=10),
    )

    answer = pipeline.answer("Koch xây dựng thế nào?")

    assert "Source 1" not in answer.answer
    assert answer.sources[0].source_name == "fractal.pdf"
    assert retriever.calls[0]["strategy"] == "parent_child"
    assert provider.requests[0].metadata["context_sources"] == 1


def test_rag_pipeline_streams_delta_then_complete_with_citations() -> None:
    retrieval_result = _retrieval_result([_chunk("c1")])
    retriever = FakeRetrieverService(retrieval_result)
    provider = FakeLLMProvider()
    pipeline = RAGPipeline(
        retriever_service=retriever,
        answer_generator=AnswerGenerator(
            llm_service=LLMService(
                config=LLMConfig(provider="fake"),
                providers={"fake": provider},
            )
        ),
    )

    events = list(pipeline.stream("Koch xây dựng thế nào?"))

    assert [event.event for event in events] == ["start", "delta", "delta", "complete"]
    assert events[-1].answer is not None
    assert events[-1].answer.answer == "Câu trả lời."
    assert events[-1].answer.sources[0].source_name == "fractal.pdf"
    assert events[-1].answer.report.llm_finish_reason == "STOP"


def test_empty_retrieval_returns_fallback_without_calling_llm() -> None:
    provider = FakeLLMProvider()
    llm_service = LLMService(config=LLMConfig(provider="fake"), providers={"fake": provider})
    generator = AnswerGenerator(llm_service=llm_service)

    answer = generator.generate(question="Không có gì?", retrieval_result=_retrieval_result([]))

    assert answer.answer == "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."
    assert answer.sources == []
    assert provider.requests == []


def test_llm_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    class FailingProvider(FakeLLMProvider):
        def generate(self, request: LLMRequest) -> LLMResponse:
            raise RuntimeError("boom")

    service = LLMService(
        config=LLMConfig(provider="failing"),
        providers={"failing": FailingProvider(provider_name="failing")},
    )

    with pytest.raises(RuntimeError):
        service.generate(LLMRequest(messages=[LLMMessage(role="user", content="Hi")]))

    assert "LLM provider failed: failing" in caplog.text

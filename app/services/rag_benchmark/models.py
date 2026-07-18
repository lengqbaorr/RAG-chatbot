from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.benchmark.models import BenchmarkCase


class RAGBenchmarkConfig(BaseModel):
    strategy: str = "parent_child"
    top_k: int = Field(default=3, ge=1)
    fetch_k: int = Field(default=8, ge=1)
    min_score: float = Field(default=0.76, ge=0.0, le=1.0)
    filters: dict | None = None
    model: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    reranker_enabled: bool = False
    reranker_model: str | None = None
    min_answer_keyword_coverage: float = Field(default=0.5, ge=0.0, le=1.0)
    empty_answer_text: str = "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."
    request_delay_seconds: float = Field(default=0.0, ge=0.0)


class RAGBenchmarkResult(BaseModel):
    case_id: str
    question: str
    answerable: bool
    topic: str | None = None
    group: str | None = None
    strategy: str
    answered: bool = False
    refused: bool = False
    answer_keyword_coverage: float = 0.0
    citation_accuracy: float = 0.0
    source_hit: bool = False
    retrieval_results: int = 0
    context_sources: int = 0
    retrieval_latency: float = 0.0
    llm_latency: float = 0.0
    total_latency: float = 0.0
    llm_provider: str | None = None
    llm_model: str | None = None
    answer_preview: str = ""
    source_names: list[str] = Field(default_factory=list)
    source_pages: list[str] = Field(default_factory=list)
    failure_type: str | None = None


class RAGBenchmarkReport(BaseModel):
    config: RAGBenchmarkConfig
    total_questions: int
    answerable_questions: int
    unanswerable_questions: int
    answer_accuracy: float = 0.0
    answer_keyword_coverage: float = 0.0
    citation_accuracy: float = 0.0
    source_hit_rate: float = 0.0
    unanswerable_rejection: float = 0.0
    avg_retrieval_latency: float = 0.0
    avg_llm_latency: float = 0.0
    avg_total_latency: float = 0.0
    failed_cases: list[RAGBenchmarkResult] = Field(default_factory=list)
    results: list[RAGBenchmarkResult] = Field(default_factory=list)


class RAGBenchmarkDataset(BaseModel):
    cases: list[BenchmarkCase]

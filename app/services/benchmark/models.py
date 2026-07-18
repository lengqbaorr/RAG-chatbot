from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class BenchmarkCase(BaseModel):
    id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    expected_source_name: str | None = None
    expected_pages: list[int] = Field(default_factory=list)
    expected_section: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)
    answerable: bool = True
    topic: str | None = None
    group: str | None = None

    @model_validator(mode="after")
    def validate_expected_labels(self) -> "BenchmarkCase":
        if self.answerable and not (
            self.expected_source_name
            or self.expected_pages
            or self.expected_section
            or self.expected_keywords
        ):
            raise ValueError("answerable case must define at least one expected label")
        return self


class BenchmarkConfig(BaseModel):
    strategy: str = "parent_child"
    top_k: int = Field(default=3, ge=1)
    fetch_k: int = Field(default=8, ge=1)
    min_score: float = Field(default=0.76, ge=0.0, le=1.0)
    filters: dict | None = None
    page_tolerance: int = Field(default=1, ge=0)


class RelevanceScore(BaseModel):
    page_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    section_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    keyword_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_match: bool = False
    final_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevant: bool = False


class BenchmarkResult(BaseModel):
    case_id: str
    question: str
    answerable: bool
    topic: str | None = None
    group: str | None = None
    strategy: str
    hit_rank: int | None = None
    reciprocal_rank: float = 0.0
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    citation_accuracy: float = 0.0
    keyword_coverage: float = 0.0
    latency: float = 0.0
    top_scores: list[float] = Field(default_factory=list)
    retrieved_sources: list[str] = Field(default_factory=list)
    retrieved_pages: list[str] = Field(default_factory=list)
    retrieved_sections: list[str] = Field(default_factory=list)
    failure_type: str | None = None


class BenchmarkReport(BaseModel):
    config: BenchmarkConfig
    total_questions: int
    answerable_questions: int
    unanswerable_questions: int
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_k: float = 0.0
    mrr: float = 0.0
    hit_rate: float = 0.0
    citation_accuracy: float = 0.0
    keyword_coverage: float = 0.0
    avg_latency: float = 0.0
    unanswerable_rejection: float = 0.0
    failed_cases: list[BenchmarkResult] = Field(default_factory=list)
    results: list[BenchmarkResult] = Field(default_factory=list)

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class EvaluationCase(BaseModel):
    id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    expected_source_name: str | None = None
    expected_source_names: list[str] = Field(default_factory=list)
    expected_pages: list[int] = Field(default_factory=list)
    expected_section: str | None = None
    expected_keywords: list[str] = Field(default_factory=list)
    answerable: bool = True
    source_id: str | None = None
    topic: str | None = None
    group: str | None = None

    @model_validator(mode="after")
    def validate_labels(self) -> "EvaluationCase":
        if self.answerable:
            has_label = any(
                [
                    self.expected_source_name,
                    self.expected_source_names,
                    self.expected_pages,
                    self.expected_section,
                    self.expected_keywords,
                ]
            )
            if not has_label:
                raise ValueError("answerable cases must include at least one expected label")
        return self


class RelevanceScore(BaseModel):
    chunk_id: str
    rank: int = Field(..., ge=1)
    page_match_score: float = Field(..., ge=0.0, le=1.0)
    section_match_score: float = Field(..., ge=0.0, le=1.0)
    keyword_match_score: float = Field(..., ge=0.0, le=1.0)
    final_relevance_score: float = Field(..., ge=0.0, le=1.0)
    is_relevant: bool


class QuestionEvaluationResult(BaseModel):
    case_id: str
    question: str
    answerable: bool
    retrieved_count: int = Field(..., ge=0)
    top_score: float = 0.0
    first_relevant_rank: int | None = None
    reciprocal_rank: float = 0.0
    precision_at_k: float = 0.0
    recall_by_k: dict[int, float] = Field(default_factory=dict)
    hit_by_k: dict[int, bool] = Field(default_factory=dict)
    citation_accuracy: float = 0.0
    keyword_coverage: float = 0.0
    unanswerable_rejected: bool | None = None
    latency: float = Field(default=0.0, ge=0.0)
    relevance_scores: list[RelevanceScore] = Field(default_factory=list)
    retrieved_sections: list[str] = Field(default_factory=list)
    retrieved_scores: list[float] = Field(default_factory=list)
    failure_type: str | None = None


class EvaluationSummary(BaseModel):
    total_questions: int = Field(..., ge=0)
    answerable_questions: int = Field(..., ge=0)
    unanswerable_questions: int = Field(..., ge=0)
    recall_at_k: dict[int, float] = Field(default_factory=dict)
    mrr: float = 0.0
    precision_at_k: float = 0.0
    citation_accuracy: float = 0.0
    keyword_coverage: float = 0.0
    unanswerable_rejection: float = 0.0
    avg_latency: float = 0.0
    failed_cases: int = 0


class EvaluationReport(BaseModel):
    config_name: str
    summary: EvaluationSummary
    results: list[QuestionEvaluationResult] = Field(default_factory=list)


class ExperimentResult(BaseModel):
    config_name: str
    recall_at_3: float = 0.0
    mrr: float = 0.0
    precision_at_5: float = 0.0
    citation_accuracy: float = 0.0
    avg_latency: float = 0.0
    failed_cases: int = 0


class ExperimentReport(BaseModel):
    results: list[ExperimentResult] = Field(default_factory=list)

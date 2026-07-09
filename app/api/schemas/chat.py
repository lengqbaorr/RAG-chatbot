from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    strategy: str = "parent_child"
    top_k: int = Field(default=3, ge=1, le=20)
    fetch_k: int | None = Field(default=None, ge=1, le=100)
    min_score: float | None = Field(default=0.78, ge=0.0, le=1.0)
    filters: dict | None = None


class SourceCitationResponse(BaseModel):
    source_id: str
    source_name: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    chunk_id: str
    score: float
    content_preview: str


class ChatReportResponse(BaseModel):
    retrieval_strategy: str
    retrieval_results: int
    context_sources: int
    llm_provider: str | None = None
    llm_model: str | None = None
    total_latency: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitationResponse]
    report: ChatReportResponse

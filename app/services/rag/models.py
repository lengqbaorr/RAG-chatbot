from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.services.llm.models import LLMUsage
from app.services.retrieval.models import RetrievalReport


class ContextSource(BaseModel):
    source_number: int = Field(..., ge=1)
    chunk_id: str
    document_id: str
    source_id: str
    source_name: str
    source_type: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    header_path: list[str] = Field(default_factory=list)
    score: float = Field(..., ge=0.0, le=1.0)
    content_preview: str


class BuiltContext(BaseModel):
    text: str
    sources: list[ContextSource] = Field(default_factory=list)
    token_count: int = Field(..., ge=0)
    truncated: bool = False


class Citation(BaseModel):
    source_number: int = Field(..., ge=1)
    source_id: str
    source_name: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    chunk_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    content_preview: str


class RAGReport(BaseModel):
    retrieval_report: RetrievalReport
    context_tokens: int = Field(..., ge=0)
    context_sources: int = Field(..., ge=0)
    context_truncated: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_latency: float = Field(default=0.0, ge=0.0)
    llm_finish_reason: str | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    total_latency: float = Field(default=0.0, ge=0.0)


class RAGAnswer(BaseModel):
    answer: str
    sources: list[Citation] = Field(default_factory=list)
    retrieval_report: RetrievalReport
    llm_provider: str | None = None
    llm_model: str | None = None
    latency: float = Field(default=0.0, ge=0.0)
    usage: LLMUsage | None = None
    report: RAGReport


class RAGStreamEvent(BaseModel):
    event: Literal["start", "delta", "complete"]
    text: str | None = None
    answer: RAGAnswer | None = None

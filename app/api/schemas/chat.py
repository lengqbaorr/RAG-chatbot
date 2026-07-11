from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    strategy: str = "parent_child"
    top_k: int = Field(default=3, ge=1, le=20)
    fetch_k: int | None = Field(default=None, ge=1, le=100)
    min_score: float | None = Field(default=0.78, ge=0.0, le=1.0)
    filters: dict | None = None
    session_id: str | None = None
    selected_source_ids: list[str] = Field(default_factory=list)


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
    llm_finish_reason: str | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    total_latency: float


class ChatResponse(BaseModel):
    session_id: str | None = None
    answer: str
    sources: list[SourceCitationResponse]
    report: ChatReportResponse


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(default="New chat", max_length=120)
    selected_source_ids: list[str] = Field(default_factory=list)


class ChatSessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    selected_source_ids: list[str] | None = None


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    selected_source_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    role: str
    content: str
    sources: list[SourceCitationResponse]
    selected_source_ids: list[str]
    status: str
    timestamp: datetime


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class ChatSessionDeleteResponse(BaseModel):
    session_id: str
    deleted: bool = True

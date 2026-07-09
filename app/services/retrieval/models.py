from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RetrievalQuery(BaseModel):
    query: str = Field(..., min_length=1)
    filters: dict | None = None
    top_k: int | None = Field(default=None, ge=1)
    fetch_k: int | None = Field(default=None, ge=1)
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    strategy: str | None = None

    @model_validator(mode="after")
    def validate_query(self) -> "RetrievalQuery":
        if not self.query.strip():
            raise ValueError("query must not be empty")
        return self


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    content: str
    metadata: dict = Field(default_factory=dict)
    score: float = Field(..., ge=0.0, le=1.0)
    distance: float
    rank: int = Field(..., ge=1)
    source_name: str
    source_type: str
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    header_path: list[str] = Field(default_factory=list)
    header_path_text: str = ""
    content_type: str
    chunk_level: str
    parent_id: str | None = None
    child_ids: list[str] = Field(default_factory=list)
    retrieval_strategy: str
    retrieved_child: "RetrievedChunk | None" = None
    child_score: float | None = None
    parent_content: str | None = None


class RetrievedContext(BaseModel):
    query: str
    normalized_query: str
    strategy: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)


class RetrievalReport(BaseModel):
    query: str
    normalized_query: str
    top_k: int = Field(..., ge=1)
    fetch_k: int = Field(..., ge=1)
    initial_results: int = Field(..., ge=0)
    after_threshold: int = Field(..., ge=0)
    after_dedup: int = Field(..., ge=0)
    final_results: int = Field(..., ge=0)
    min_score: float = 0.0
    max_score: float = 0.0
    avg_score: float = 0.0
    retrieval_time: float = Field(..., ge=0.0)
    embedding_time: float = Field(..., ge=0.0)
    vector_search_time: float = Field(..., ge=0.0)
    strategy: str


class RetrievalResult(BaseModel):
    query: str
    normalized_query: str
    context: RetrievedContext
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    report: RetrievalReport

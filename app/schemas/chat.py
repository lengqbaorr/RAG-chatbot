from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class Source(BaseModel):
    document_id: str
    title: str | None = None
    source: str | None = None
    page_number: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []

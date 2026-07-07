from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    txt = "txt"
    markdown = "md"
    pdf = "pdf"
    docx = "docx"
    url = "url"
    image = "image"


class DocumentMetadata(BaseModel):
    document_id: str
    document_type: DocumentType
    source: str
    title: str | None = None
    page_number: int | None = None
    user_id: str | None = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    mime_type: str | None = None


class Document(BaseModel):
    text: str
    metadata: DocumentMetadata

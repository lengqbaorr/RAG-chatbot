from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    source_id: str
    source_name: str
    documents: int = Field(..., ge=0)
    chunks: int = Field(..., ge=0)
    embedded: int = Field(..., ge=0)
    upserted: int = Field(..., ge=0)
    excluded: int = Field(..., ge=0)
    collection: str


class DocumentInfoResponse(BaseModel):
    source_id: str
    source_name: str
    source_type: str | None = None
    chunk_count: int = Field(..., ge=0)


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfoResponse]


class DocumentDeleteResponse(BaseModel):
    source_id: str
    deleted_count: int = Field(..., ge=0)

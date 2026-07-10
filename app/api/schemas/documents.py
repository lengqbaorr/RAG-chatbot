from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentUrlUploadRequest(BaseModel):
    url: str = Field(..., min_length=8)
    title: str | None = Field(default=None, max_length=255)


class DocumentUploadResponse(BaseModel):
    job_id: str | None = None
    source_id: str
    status: str
    duplicate: bool = False
    source_name: str | None = None
    documents: int = Field(default=0, ge=0)
    chunks: int = Field(default=0, ge=0)
    embedded: int = Field(default=0, ge=0)
    upserted: int = Field(default=0, ge=0)
    excluded: int = Field(default=0, ge=0)
    collection: str | None = None


class DocumentInfoResponse(BaseModel):
    source_id: str
    source_name: str
    source_type: str | None = None
    chunk_count: int = Field(..., ge=0)
    status: str = "PENDING"


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfoResponse]


class DocumentDeleteResponse(BaseModel):
    source_id: str
    deleted_count: int = Field(default=0, ge=0)
    deleted_vectors: int = Field(default=0, ge=0)
    deleted_chunks: int = Field(default=0, ge=0)
    raw_file_deleted: bool = False

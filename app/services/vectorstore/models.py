import json
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chunk import ChunkMetadata
from app.services.embedding.models import EmbeddedChunk


class VectorRecord(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    content: str
    embedding_text: str
    vector: list[float] = Field(..., min_length=1)
    metadata: dict
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
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int = Field(..., ge=1)
    embedding_version: str
    embedding_text_hash: str

    @classmethod
    def from_embedded_chunk(cls, ec: EmbeddedChunk) -> "VectorRecord":
        meta = ec.metadata
        hp = meta.header_path or []
        return cls(
            chunk_id=ec.chunk_id,
            document_id=ec.document_id,
            source_id=meta.source_id,
            content=ec.content,
            embedding_text=ec.embedding_text,
            vector=ec.vector,
            metadata=meta.model_dump(),
            source_name=meta.source_name,
            source_type=meta.source_type.value,
            page_start=meta.page_start,
            page_end=meta.page_end,
            section_title=meta.section_title,
            header_path=hp,
            header_path_text=" > ".join(hp),
            content_type=meta.content_type.value,
            chunk_level=meta.chunk_level,
            parent_id=meta.parent_id,
            child_ids=meta.child_ids,
            embedding_provider=ec.embedding_provider,
            embedding_model=ec.embedding_model,
            embedding_dimension=ec.embedding_dimension,
            embedding_version=ec.embedding_version,
            embedding_text_hash=ec.embedding_text_hash,
        )


class VectorSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    content: str
    embedding_text: str
    metadata: dict
    score: float = Field(..., ge=0.0, le=1.0)
    distance: float
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
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int = Field(..., ge=1)
    embedding_version: str
    embedding_text_hash: str


class VectorStoreUpsertResult(BaseModel):
    total_input: int = Field(..., ge=0)
    skipped_excluded: int = Field(..., ge=0)
    upserted_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    collection_name: str


class VectorStoreDeleteResult(BaseModel):
    deleted_count: int = Field(..., ge=0)


class VectorStoreStats(BaseModel):
    total_count: int = Field(..., ge=0)
    collection_name: str
    embedding_model: str
    embedding_dimension: int = Field(..., ge=1)
    distance_metric: str

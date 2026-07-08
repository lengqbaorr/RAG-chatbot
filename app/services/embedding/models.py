from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.chunk import ChunkMetadata, DocumentChunk


class EmbeddingInput(BaseModel):
    chunk: DocumentChunk
    embedding_text: str = Field(..., min_length=1)
    embedding_text_hash: str = Field(..., min_length=1)


class EmbeddedChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    embedding_text: str
    embedding_text_hash: str
    vector: list[float] = Field(..., min_length=1)
    metadata: ChunkMetadata
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int = Field(..., ge=1)
    embedding_version: str
    embedded_at: datetime = Field(default_factory=datetime.utcnow)


class EmbeddingReport(BaseModel):
    total_chunks: int = Field(..., ge=0)
    excluded_chunks: int = Field(..., ge=0)
    cache_hits: int = Field(..., ge=0)
    cache_misses: int = Field(..., ge=0)
    embedded_count: int = Field(..., ge=0)
    provider_name: str
    model_name: str
    dimension: int = Field(..., ge=1)


class EmbeddingBatchResult(BaseModel):
    chunks: list[EmbeddedChunk]
    report: EmbeddingReport

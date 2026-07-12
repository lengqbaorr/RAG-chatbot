from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class DocumentStatus(StrEnum):
    pending = "PENDING"
    indexing = "INDEXING"
    completed = "COMPLETED"
    failed = "FAILED"
    deleted = "DELETED"


@dataclass(frozen=True)
class DocumentRecord:
    source_id: str
    source_name: str
    original_filename: str
    mime_type: str | None
    file_size: int
    sha256: str
    raw_path: str
    upload_time: datetime
    status: DocumentStatus
    owner: str | None = None
    language: str | None = None
    page_count: int = 0
    chunk_count: int = 0
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    collection_name: str | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_id: str
    parent_id: str | None
    page_start: int | None
    page_end: int | None
    section_title: str | None
    header_path: list[str] = field(default_factory=list)
    token_count: int = 0
    retrieval_excluded: bool = False
    content_hash: str = ""
    content: str = ""


@dataclass(frozen=True)
class DocumentCreate:
    source_id: str
    source_name: str
    original_filename: str
    mime_type: str | None
    file_size: int
    sha256: str
    raw_path: str
    status: DocumentStatus = DocumentStatus.pending
    owner: str | None = None


@dataclass(frozen=True)
class DocumentDeleteReport:
    source_id: str
    deleted_vectors: int
    deleted_chunks: int
    raw_file_deleted: bool


@dataclass(frozen=True)
class DocumentInfo:
    source_id: str
    source_name: str
    source_type: str | None
    chunk_count: int
    status: str = DocumentStatus.pending.value


@dataclass(frozen=True)
class DocumentPreview:
    source_id: str
    source_name: str
    source_type: str
    mime_type: str | None
    preview_kind: str
    page_count: int
    content: str | None = None
    truncated: bool = False


@dataclass(frozen=True)
class DocumentChunkPreview:
    chunk_id: str
    source_id: str
    content: str
    page_start: int | None
    page_end: int | None
    section_title: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

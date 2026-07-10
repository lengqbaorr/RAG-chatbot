from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobStatus(StrEnum):
    pending = "PENDING"
    running = "RUNNING"
    failed = "FAILED"
    completed = "COMPLETED"
    cancelled = "CANCELLED"


class JobStage(StrEnum):
    uploading = "Uploading"
    loading = "Loading"
    chunking = "Chunking"
    embedding = "Embedding"
    vectorstore = "VectorStore"
    finishing = "Finishing"


@dataclass(frozen=True)
class IndexJobRecord:
    job_id: str
    source_id: str
    status: JobStatus
    progress: int
    current_stage: JobStage
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

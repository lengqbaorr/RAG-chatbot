from __future__ import annotations

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    job_id: str
    source_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)
    current_stage: str
    error_message: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]

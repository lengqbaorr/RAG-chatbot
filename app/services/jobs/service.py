from __future__ import annotations

import uuid
from datetime import datetime

from app.core.exceptions import AppError
from app.services.jobs.models import IndexJobRecord, JobStage, JobStatus
from app.services.jobs.repository import JobRepository


class JobNotFoundError(AppError):
    status_code = 404
    error_code = "job_not_found"


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def create_index_job(self, source_id: str) -> IndexJobRecord:
        return self.repository.create_job(job_id=uuid.uuid4().hex, source_id=source_id)

    def get_job(self, job_id: str) -> IndexJobRecord:
        job = self.repository.get_job(job_id)
        if job is None:
            raise JobNotFoundError(f"Job not found: {job_id}")
        return job

    def list_jobs(self) -> list[IndexJobRecord]:
        return self.repository.list_jobs()

    def mark_running(self, job_id: str, *, stage: JobStage, progress: int) -> None:
        self.repository.update_job(
            job_id,
            status=JobStatus.running,
            stage=stage,
            progress=progress,
            started_at=datetime.utcnow(),
        )

    def update_progress(self, job_id: str, *, stage: JobStage, progress: int) -> None:
        self.repository.update_job(job_id, status=JobStatus.running, stage=stage, progress=progress)

    def mark_completed(self, job_id: str) -> None:
        self.repository.update_job(
            job_id,
            status=JobStatus.completed,
            stage=JobStage.finishing,
            progress=100,
            finished_at=datetime.utcnow(),
        )

    def mark_failed(self, job_id: str, error_message: str) -> None:
        self.repository.update_job(
            job_id,
            status=JobStatus.failed,
            progress=100,
            error_message=error_message[:2000],
            finished_at=datetime.utcnow(),
        )

    def pending_count(self) -> int:
        return self.repository.count_pending()

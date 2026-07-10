from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_job_service
from app.api.schemas.jobs import JobListResponse, JobResponse
from app.services.jobs import IndexJobRecord, JobService

router = APIRouter(prefix="/jobs")


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, job_service: JobService = Depends(get_job_service)) -> JobResponse:
    return _to_response(job_service.get_job(job_id))


@router.get("", response_model=JobListResponse)
def list_jobs(job_service: JobService = Depends(get_job_service)) -> JobListResponse:
    return JobListResponse(jobs=[_to_response(job) for job in job_service.list_jobs()])


def _to_response(job: IndexJobRecord) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        source_id=job.source_id,
        status=job.status.value,
        progress=job.progress,
        current_stage=job.current_stage.value,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )

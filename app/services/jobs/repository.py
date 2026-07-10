from __future__ import annotations

import sqlite3
from datetime import datetime

from app.db import Database
from app.services.jobs.models import IndexJobRecord, JobStage, JobStatus


class JobRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_job(self, *, job_id: str, source_id: str) -> IndexJobRecord:
        now = datetime.utcnow().isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO index_jobs (
                    job_id, source_id, status, progress, current_stage,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    source_id,
                    JobStatus.pending.value,
                    0,
                    JobStage.uploading.value,
                    now,
                    now,
                ),
            )
        job = self.get_job(job_id)
        if job is None:
            raise RuntimeError("job insert failed")
        return job

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        stage: JobStage | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> IndexJobRecord | None:
        fields: dict[str, object] = {"updated_at": datetime.utcnow().isoformat()}
        if status is not None:
            fields["status"] = status.value
        if progress is not None:
            fields["progress"] = max(0, min(100, progress))
        if stage is not None:
            fields["current_stage"] = stage.value
        if error_message is not None:
            fields["error_message"] = error_message
        if started_at is not None:
            fields["started_at"] = started_at.isoformat()
        if finished_at is not None:
            fields["finished_at"] = finished_at.isoformat()

        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [job_id]
        with self.db.connect() as conn:
            conn.execute(f"UPDATE index_jobs SET {assignments} WHERE job_id = ?", values)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> IndexJobRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM index_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self) -> list[IndexJobRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM index_jobs ORDER BY created_at DESC",
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def count_pending(self) -> int:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM index_jobs WHERE status IN (?, ?)",
                (JobStatus.pending.value, JobStatus.running.value),
            ).fetchone()
        return int(row["c"])

    def _row_to_job(self, row: sqlite3.Row) -> IndexJobRecord:
        return IndexJobRecord(
            job_id=row["job_id"],
            source_id=row["source_id"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            current_stage=JobStage(row["current_stage"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            error_message=row["error_message"],
        )

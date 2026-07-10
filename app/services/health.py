from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path

from app.db import Database
from app.services.jobs import JobService
from app.services.llm.service import LLMService
from app.services.vectorstore.interfaces import BaseVectorStore


@dataclass(frozen=True)
class HealthStatus:
    app: str
    embedding_service: str
    vector_store: str
    llm_provider: str
    collection: str | None
    collection_count: int
    ready: bool
    database: str = "unknown"
    upload_dir: str | None = None
    disk_free_bytes: int | None = None
    pending_jobs: int = 0


class HealthService:
    def __init__(
        self,
        *,
        vector_store: BaseVectorStore | None = None,
        llm_service: LLMService | None = None,
        embedding_service: object | None = None,
        database: Database | None = None,
        job_service: JobService | None = None,
        upload_dir: str | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.database = database
        self.job_service = job_service
        self.upload_dir = upload_dir

    def check(self) -> HealthStatus:
        collection = None
        count = 0
        vector_status = "unavailable"
        if self.vector_store is not None:
            try:
                stats = self.vector_store.stats()
                collection = stats.collection_name
                count = stats.total_count
                vector_status = "ok"
            except Exception:
                vector_status = "error"

        embedding_status = "ok" if self.embedding_service is not None else "unavailable"
        llm_provider = self.llm_service.config.provider if self.llm_service is not None else "unavailable"
        database_status = self._database_status()
        disk_free = self._disk_free()
        pending_jobs = self.job_service.pending_count() if self.job_service is not None else 0
        ready = (
            embedding_status == "ok"
            and vector_status == "ok"
            and database_status == "ok"
            and llm_provider != "unavailable"
        )
        return HealthStatus(
            app="ok",
            database=database_status,
            embedding_service=embedding_status,
            vector_store=vector_status,
            llm_provider=llm_provider,
            upload_dir=self.upload_dir,
            disk_free_bytes=disk_free,
            collection=collection,
            collection_count=count,
            pending_jobs=pending_jobs,
            ready=ready,
        )

    def _database_status(self) -> str:
        if self.database is None:
            return "unavailable"
        try:
            with self.database.connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return "ok"
        except Exception:
            return "error"

    def _disk_free(self) -> int | None:
        if not self.upload_dir:
            return None
        try:
            Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
            return shutil.disk_usage(self.upload_dir).free
        except Exception:
            return None

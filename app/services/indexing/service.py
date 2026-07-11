from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

from app.core.exceptions import BadRequestError
from app.services.document.models import DocumentCreate, DocumentStatus
from app.services.document.repository import DocumentRepository
from app.services.document.validators import safe_filename, validate_extension, validate_http_url
from app.services.indexing.models import IndexingConfig, IndexingTask, UploadSubmission
from app.services.indexing.queue import IndexingQueue
from app.services.jobs.models import JobStatus
from app.services.jobs.service import JobService


class IndexingService:
    def __init__(
        self,
        *,
        document_repository: DocumentRepository | None = None,
        job_service: JobService | None = None,
        queue: IndexingQueue | None = None,
        config: IndexingConfig | None = None,
        **legacy_kwargs,
    ) -> None:
        self.document_repository = document_repository
        self.job_service = job_service
        self.queue = queue
        self.config = config or IndexingConfig()
        self._legacy_kwargs = legacy_kwargs

    def submit_upload(
        self,
        *,
        filename: str,
        file_obj: BinaryIO,
        mime_type: str | None = None,
        owner: str | None = None,
    ) -> UploadSubmission:
        source_name = safe_filename(filename)
        validate_extension(source_name, self.config.allowed_extensions)
        if self.document_repository is None or self.job_service is None or self.queue is None:
            temp_path = Path(self.config.upload_dir) / f"{uuid.uuid4().hex}_{source_name}"
            self._save_with_hash(file_obj, temp_path)
            temp_path.unlink(missing_ok=True)
            return UploadSubmission(job_id="", source_id="", status=JobStatus.completed.value)

        upload_dir = Path(self.config.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        raw_id = uuid.uuid4().hex
        raw_path = upload_dir / f"{raw_id}_{source_name}"
        file_size, sha256 = self._save_with_hash(file_obj, raw_path)

        duplicate = self.document_repository.find_by_hash(sha256, file_size)
        if duplicate is not None and self.config.duplicate_policy == "skip":
            raw_path.unlink(missing_ok=True)
            if duplicate.status == DocumentStatus.failed:
                return self._retry_failed_duplicate(duplicate.source_id)
            job = self.job_service.create_index_job(duplicate.source_id)
            self.job_service.repository.update_job(
                job.job_id,
                status=JobStatus.completed,
                progress=100,
                error_message="duplicate_skipped",
            )
            return UploadSubmission(
                job_id=job.job_id,
                source_id=duplicate.source_id,
                status=JobStatus.completed.value,
                duplicate=True,
            )

        source_id = raw_id
        self.document_repository.create_document(
            DocumentCreate(
                source_id=source_id,
                source_name=source_name,
                original_filename=source_name,
                mime_type=mime_type,
                file_size=file_size,
                sha256=sha256,
                raw_path=str(raw_path),
                owner=owner,
            )
        )
        job = self.job_service.create_index_job(source_id)
        self.queue.put(IndexingTask(job_id=job.job_id, source_id=source_id))
        return UploadSubmission(job_id=job.job_id, source_id=source_id, status=JobStatus.running.value)

    def submit_url(
        self,
        *,
        url: str,
        title: str | None = None,
        owner: str | None = None,
    ) -> UploadSubmission:
        clean_url = validate_http_url(url)
        source_name = safe_filename(title or self._source_name_from_url(clean_url))
        sha256 = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()
        file_size = len(clean_url.encode("utf-8"))

        if self.document_repository is None or self.job_service is None or self.queue is None:
            return UploadSubmission(job_id="", source_id="", status=JobStatus.completed.value)

        duplicate = self.document_repository.find_by_hash(sha256, file_size)
        if duplicate is not None and self.config.duplicate_policy == "skip":
            if duplicate.status == DocumentStatus.failed:
                return self._retry_failed_duplicate(duplicate.source_id)
            job = self.job_service.create_index_job(duplicate.source_id)
            self.job_service.repository.update_job(
                job.job_id,
                status=JobStatus.completed,
                progress=100,
                error_message="duplicate_skipped",
            )
            return UploadSubmission(
                job_id=job.job_id,
                source_id=duplicate.source_id,
                status=JobStatus.completed.value,
                duplicate=True,
            )

        source_id = uuid.uuid4().hex
        self.document_repository.create_document(
            DocumentCreate(
                source_id=source_id,
                source_name=source_name,
                original_filename=clean_url,
                mime_type="text/html",
                file_size=file_size,
                sha256=sha256,
                raw_path=clean_url,
                owner=owner,
            )
        )
        job = self.job_service.create_index_job(source_id)
        self.queue.put(IndexingTask(job_id=job.job_id, source_id=source_id))
        return UploadSubmission(job_id=job.job_id, source_id=source_id, status=JobStatus.running.value)

    def submit_reindex(self, source_id: str) -> UploadSubmission:
        document = self.document_repository.get_document(source_id)
        if document is None or document.deleted_at is not None:
            from app.core.exceptions import DocumentNotFoundError

            raise DocumentNotFoundError(f"Document not found: {source_id}")
        job = self.job_service.create_index_job(source_id)
        self.queue.put(IndexingTask(job_id=job.job_id, source_id=source_id))
        return UploadSubmission(job_id=job.job_id, source_id=source_id, status=JobStatus.running.value)

    def _retry_failed_duplicate(self, source_id: str) -> UploadSubmission:
        self.document_repository.update_document(source_id, status=DocumentStatus.pending)
        job = self.job_service.create_index_job(source_id)
        self.queue.put(IndexingTask(job_id=job.job_id, source_id=source_id))
        return UploadSubmission(
            job_id=job.job_id,
            source_id=source_id,
            status=JobStatus.running.value,
            duplicate=True,
        )

    def _save_with_hash(self, file_obj: BinaryIO, target_path: Path) -> tuple[int, str]:
        max_bytes = self.config.max_upload_mb * 1024 * 1024
        total = 0
        digest = hashlib.sha256()
        try:
            with target_path.open("wb") as out:
                while True:
                    chunk = file_obj.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise BadRequestError(
                            "Uploaded file is too large",
                            details={"max_upload_mb": self.config.max_upload_mb},
                        )
                    digest.update(chunk)
                    out.write(chunk)
        except Exception:
            target_path.unlink(missing_ok=True)
            raise
        if total == 0:
            target_path.unlink(missing_ok=True)
            raise BadRequestError("Uploaded file is empty")
        return total, digest.hexdigest()

    @staticmethod
    def _source_name_from_url(url: str) -> str:
        parsed = urlparse(url)
        path_name = Path(parsed.path).name
        if path_name:
            return path_name
        return parsed.netloc

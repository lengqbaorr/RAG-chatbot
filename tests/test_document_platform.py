from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.db import Database
from app.services.document import DocumentCreate, DocumentRepository, DocumentService, DocumentStatus
from app.services.indexing import IndexingConfig, IndexingService
from app.services.indexing.queue import InMemoryIndexingQueue
from app.services.jobs import JobRepository, JobService, JobStage, JobStatus
from app.services.vectorstore.models import VectorStoreDeleteResult, VectorStoreStats


class FakeVectorStore:
    def __init__(self) -> None:
        self.deleted_source_ids: list[str] = []

    def delete_by_source_id(self, source_id: str) -> VectorStoreDeleteResult:
        self.deleted_source_ids.append(source_id)
        return VectorStoreDeleteResult(deleted_count=3)

    def stats(self) -> VectorStoreStats:
        return VectorStoreStats(
            total_count=0,
            collection_name="test",
            embedding_model="",
            embedding_dimension=1024,
            distance_metric="cosine",
        )


def _db(tmp_path: Path) -> Database:
    db = Database(str(tmp_path / "metadata.db"))
    db.initialize()
    return db


def test_document_repository_crud_and_hash_lookup(tmp_path: Path) -> None:
    repo = DocumentRepository(_db(tmp_path))
    doc = repo.create_document(
        DocumentCreate(
            source_id="src-1",
            source_name="file.pdf",
            original_filename="file.pdf",
            mime_type="application/pdf",
            file_size=3,
            sha256="abc",
            raw_path=str(tmp_path / "file.pdf"),
        )
    )

    assert doc.status == DocumentStatus.pending
    assert repo.find_by_hash("abc", 3).source_id == "src-1"

    updated = repo.update_document("src-1", status=DocumentStatus.completed, chunk_count=10)

    assert updated.status == DocumentStatus.completed
    assert repo.completed_source_ids() == ["src-1"]


def test_job_service_progress(tmp_path: Path) -> None:
    db = _db(tmp_path)
    DocumentRepository(db).create_document(
        DocumentCreate(
            source_id="src-1",
            source_name="file.pdf",
            original_filename="file.pdf",
            mime_type="application/pdf",
            file_size=3,
            sha256="abc",
            raw_path=str(tmp_path / "file.pdf"),
        )
    )
    service = JobService(JobRepository(db))
    job = service.create_index_job("src-1")

    service.mark_running(job.job_id, stage=JobStage.loading, progress=15)
    running = service.get_job(job.job_id)

    assert running.status == JobStatus.running
    assert running.progress == 15

    service.mark_completed(job.job_id)

    assert service.get_job(job.job_id).status == JobStatus.completed


def test_indexing_service_skips_duplicate_by_hash(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = DocumentRepository(db)
    job_service = JobService(JobRepository(db))
    queue = InMemoryIndexingQueue()
    upload_dir = tmp_path / "raw"
    service = IndexingService(
        document_repository=repo,
        job_service=job_service,
        queue=queue,
        config=IndexingConfig(upload_dir=str(upload_dir), duplicate_policy="skip"),
    )

    first = service.submit_upload(
        filename="file.pdf",
        file_obj=BytesIO(b"same-content"),
        mime_type="application/pdf",
    )
    second = service.submit_upload(
        filename="file.pdf",
        file_obj=BytesIO(b"same-content"),
        mime_type="application/pdf",
    )

    assert first.source_id != ""
    assert second.source_id == first.source_id
    assert second.duplicate is True
    assert len(repo.list_documents()) == 1


def test_indexing_service_submits_url_and_skips_duplicate(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = DocumentRepository(db)
    job_service = JobService(JobRepository(db))
    queue = InMemoryIndexingQueue()
    service = IndexingService(
        document_repository=repo,
        job_service=job_service,
        queue=queue,
        config=IndexingConfig(upload_dir=str(tmp_path / "raw"), duplicate_policy="skip"),
    )

    first = service.submit_url(url="https://example.com/article", title="Article")
    second = service.submit_url(url="https://example.com/article", title="Article")
    document = repo.get_document(first.source_id)

    assert document is not None
    assert document.raw_path == "https://example.com/article"
    assert document.mime_type == "text/html"
    assert second.source_id == first.source_id
    assert second.duplicate is True
    assert queue.get(timeout=0).source_id == first.source_id


def test_indexing_service_retries_failed_duplicate_url(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = DocumentRepository(db)
    job_service = JobService(JobRepository(db))
    queue = InMemoryIndexingQueue()
    service = IndexingService(
        document_repository=repo,
        job_service=job_service,
        queue=queue,
        config=IndexingConfig(upload_dir=str(tmp_path / "raw"), duplicate_policy="skip"),
    )

    first = service.submit_url(url="https://arxiv.org/pdf/1912.13318", title="LayoutLM")
    queue.get(timeout=0)
    repo.update_document(first.source_id, status=DocumentStatus.failed)

    retried = service.submit_url(
        url="https://arxiv.org/pdf/1912.13318",
        title="LayoutLM",
    )

    assert retried.source_id == first.source_id
    assert retried.status == JobStatus.running.value
    assert retried.duplicate is True
    assert repo.get_document(first.source_id).status == DocumentStatus.pending
    assert queue.get(timeout=0).source_id == first.source_id


def test_document_delete_removes_vectors_chunks_and_raw_file(tmp_path: Path) -> None:
    db = _db(tmp_path)
    repo = DocumentRepository(db)
    raw = tmp_path / "file.pdf"
    raw.write_bytes(b"pdf")
    repo.create_document(
        DocumentCreate(
            source_id="src-1",
            source_name="file.pdf",
            original_filename="file.pdf",
            mime_type="application/pdf",
            file_size=3,
            sha256="abc",
            raw_path=str(raw),
        )
    )
    vector_store = FakeVectorStore()
    service = DocumentService(repository=repo, vector_store=vector_store)

    report = service.delete_document("src-1")

    assert report.deleted_vectors == 3
    assert report.raw_file_deleted is True
    assert vector_store.deleted_source_ids == ["src-1"]
    assert repo.get_document("src-1").status == DocumentStatus.deleted

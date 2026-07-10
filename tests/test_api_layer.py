from __future__ import annotations

from typing import BinaryIO

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_document_service, get_indexing_service, get_job_service, get_rag_pipeline
from app.core.exceptions import DocumentNotFoundError
from app.main import app
from app.services.document import DocumentDeleteReport, DocumentInfo
from app.services.indexing import IndexingConfig, IndexingReport, IndexingService
from app.services.indexing.models import UploadSubmission
from app.services.llm.models import LLMUsage
from app.services.rag.models import Citation, RAGAnswer, RAGReport
from app.services.retrieval.models import RetrievalReport


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class FakeRAGPipeline:
    def answer(self, question: str, **kwargs) -> RAGAnswer:
        report = _retrieval_report(strategy=kwargs["strategy"])
        return RAGAnswer(
            answer=f"Trả lời cho: {question} [Source 1]",
            sources=[
                Citation(
                    source_number=1,
                    source_id="src-1",
                    source_name="file.pdf",
                    page_start=2,
                    page_end=4,
                    section_title="2.1. Bông tuyết Koch",
                    chunk_id="chunk-1",
                    score=0.858,
                    content_preview="Bông tuyết Koch...",
                )
            ],
            retrieval_report=report,
            llm_provider="gemini",
            llm_model="gemini-2.5-flash",
            latency=0.12,
            usage=LLMUsage(total_tokens=100),
            report=RAGReport(
                retrieval_report=report,
                context_tokens=120,
                context_sources=1,
                llm_provider="gemini",
                llm_model="gemini-2.5-flash",
                total_latency=0.12,
            ),
        )


class FakeIndexingService:
    def submit_upload(self, *, filename: str, file_obj: BinaryIO, mime_type: str | None = None):
        del file_obj, mime_type
        return UploadSubmission(job_id="job-1", source_id="src-1", status="RUNNING")

    def submit_url(self, *, url: str, title: str | None = None, owner: str | None = None):
        del url, title, owner
        return UploadSubmission(job_id="job-url-1", source_id="src-url-1", status="RUNNING")

    def index_upload(self, *, filename: str, file_obj: BinaryIO) -> IndexingReport:
        del file_obj
        return IndexingReport(
            source_id="src-1",
            source_name=filename,
            documents=23,
            chunks=31,
            embedded=30,
            upserted=30,
            excluded=1,
            collection="personal_docs_bge_m3_1024",
        )


class FakeDocumentService:
    def list_documents(self) -> list[DocumentInfo]:
        return [
            DocumentInfo(
                source_id="src-1",
                source_name="file.pdf",
                source_type="pdf",
                chunk_count=30,
            )
        ]

    def get_document(self, source_id: str) -> DocumentInfo:
        if source_id != "src-1":
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return self.list_documents()[0]

    def delete_document(self, source_id: str) -> DocumentDeleteReport:
        if source_id != "src-1":
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return DocumentDeleteReport(
            source_id=source_id,
            deleted_vectors=30,
            deleted_chunks=30,
            raw_file_deleted=True,
        )


class FakeJob:
    def __init__(self, job_id: str = "job-1") -> None:
        from datetime import datetime
        from app.services.jobs import JobStage, JobStatus

        self.job_id = job_id
        self.source_id = "src-1"
        self.status = JobStatus.running
        self.progress = 40
        self.current_stage = JobStage.chunking
        self.error_message = None
        self.created_at = datetime(2026, 1, 1)
        self.updated_at = datetime(2026, 1, 1)
        self.started_at = datetime(2026, 1, 1)
        self.finished_at = None


class FakeJobService:
    def get_job(self, job_id: str):
        if job_id != "job-1":
            from app.services.jobs import JobNotFoundError

            raise JobNotFoundError(f"Job not found: {job_id}")
        return FakeJob(job_id)

    def list_jobs(self):
        return [FakeJob()]


class DummyLoader:
    def load(self, loader_input):
        del loader_input
        return []


class DummyChunker:
    def chunk_documents(self, docs):
        del docs
        return []


class DummyEmbeddingService:
    def embed_chunks(self, chunks):
        del chunks
        raise AssertionError("embedding should not be called for invalid upload")


class DummyVectorStoreService:
    def upsert_embeddings(self, chunks):
        del chunks
        raise AssertionError("vector store should not be called for invalid upload")


def test_post_chat_with_mock_rag_pipeline() -> None:
    app.dependency_overrides[get_rag_pipeline] = lambda: FakeRAGPipeline()
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "question": "Bông tuyết Koch được xây dựng như thế nào?",
            "strategy": "parent_child",
            "top_k": 3,
            "min_score": 0.78,
            "filters": {"source_type": "pdf"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sources"][0]["source_name"] == "file.pdf"
    assert body["report"]["llm_provider"] == "gemini"
    assert body["report"]["retrieval_strategy"] == "parent_child"


def test_upload_document_with_mock_indexing_service() -> None:
    app.dependency_overrides[get_indexing_service] = lambda: FakeIndexingService()
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("file.pdf", b"fake pdf", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["source_id"] == "src-1"
    assert response.json()["job_id"] == "job-1"
    assert response.json()["status"] == "RUNNING"


def test_upload_url_with_mock_indexing_service() -> None:
    app.dependency_overrides[get_indexing_service] = lambda: FakeIndexingService()
    client = TestClient(app)

    response = client.post(
        "/documents/url",
        json={"url": "https://example.com/article", "title": "Example article"},
    )

    assert response.status_code == 200
    assert response.json()["source_id"] == "src-url-1"
    assert response.json()["job_id"] == "job-url-1"


def test_upload_image_is_allowed_for_ocr(tmp_path) -> None:
    service = _invalid_upload_service(max_upload_mb=1, upload_dir=str(tmp_path))
    app.dependency_overrides[get_indexing_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("scan.png", b"fake image bytes", "image/png")},
    )

    assert response.status_code == 200


def test_job_api_with_mock_job_service() -> None:
    app.dependency_overrides[get_job_service] = lambda: FakeJobService()
    client = TestClient(app)

    detail = client.get("/jobs/job-1")
    listing = client.get("/jobs")

    assert detail.status_code == 200
    assert detail.json()["job_id"] == "job-1"
    assert detail.json()["progress"] == 40
    assert listing.status_code == 200
    assert listing.json()["jobs"][0]["source_id"] == "src-1"


def test_upload_rejects_unsupported_extension(tmp_path) -> None:
    service = _invalid_upload_service(max_upload_mb=1, upload_dir=str(tmp_path))
    app.dependency_overrides[get_indexing_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("malware.exe", b"bad", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_upload_rejects_file_too_large(tmp_path) -> None:
    service = _invalid_upload_service(max_upload_mb=0, upload_dir=str(tmp_path))
    app.dependency_overrides[get_indexing_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/documents/upload",
        files={"file": ("large.pdf", b"x", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_delete_document_by_source_id() -> None:
    app.dependency_overrides[get_document_service] = lambda: FakeDocumentService()
    client = TestClient(app)

    response = client.delete("/documents/src-1")

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "src-1"
    assert body["deleted_count"] == 30
    assert body["deleted_vectors"] == 30


def test_document_not_found_error_mapping() -> None:
    app.dependency_overrides[get_document_service] = lambda: FakeDocumentService()
    client = TestClient(app)

    response = client.delete("/documents/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def _invalid_upload_service(*, max_upload_mb: int, upload_dir: str) -> IndexingService:
    return IndexingService(
        loader=DummyLoader(),
        chunker=DummyChunker(),
        embedding_service=DummyEmbeddingService(),
        vector_store_service=DummyVectorStoreService(),
        config=IndexingConfig(
            upload_dir=upload_dir,
            max_upload_mb=max_upload_mb,
            allowed_extensions=("pdf", "docx", "txt", "md", "png", "jpg", "jpeg"),
        ),
    )


def _retrieval_report(*, strategy: str) -> RetrievalReport:
    return RetrievalReport(
        query="Koch?",
        normalized_query="Koch?",
        top_k=3,
        fetch_k=10,
        initial_results=1,
        after_threshold=1,
        after_dedup=1,
        final_results=1,
        min_score=0.858,
        max_score=0.858,
        avg_score=0.858,
        retrieval_time=0.01,
        embedding_time=0.001,
        vector_search_time=0.002,
        strategy=strategy,
    )

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.core.exceptions import DocumentNotFoundError, VectorStoreAppError
from app.services.document.models import DocumentDeleteReport, DocumentInfo, DocumentRecord
from app.services.document.repository import DocumentRepository
from app.services.vectorstore.interfaces import BaseVectorStore


class DocumentService:
    def __init__(self, *, repository: DocumentRepository, vector_store: BaseVectorStore) -> None:
        self.repository = repository
        self.vector_store = vector_store

    def list_documents(self) -> list[DocumentInfo]:
        return [self._to_info(doc) for doc in self.repository.list_documents()]

    def get_document(self, source_id: str) -> DocumentInfo:
        doc = self.repository.get_document(source_id)
        if doc is None or doc.deleted_at is not None:
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return self._to_info(doc)

    def get_record(self, source_id: str) -> DocumentRecord:
        doc = self.repository.get_document(source_id)
        if doc is None or doc.deleted_at is not None:
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return doc

    def delete_document(self, source_id: str) -> DocumentDeleteReport:
        doc = self.get_record(source_id)
        try:
            vector_result = self.vector_store.delete_by_source_id(source_id)
        except Exception as exc:
            raise VectorStoreAppError("Vector store delete failed") from exc
        deleted_chunks = self.repository.delete_chunks(source_id)
        raw_deleted = self._delete_raw_file(doc.raw_path)
        self.repository.soft_delete_document(source_id)
        return DocumentDeleteReport(
            source_id=source_id,
            deleted_vectors=vector_result.deleted_count,
            deleted_chunks=deleted_chunks,
            raw_file_deleted=raw_deleted,
        )

    def completed_source_ids(self) -> list[str]:
        return self.repository.completed_source_ids()

    def _delete_raw_file(self, raw_path: str) -> bool:
        try:
            path = Path(raw_path)
            if path.exists():
                path.unlink()
                return True
        except PermissionError:
            return False
        return False

    def _to_info(self, doc: DocumentRecord) -> DocumentInfo:
        source_type = self._source_type(doc)
        return DocumentInfo(
            source_id=doc.source_id,
            source_name=doc.source_name,
            source_type=source_type,
            chunk_count=doc.chunk_count,
            status=doc.status.value,
        )

    @staticmethod
    def _source_type(doc: DocumentRecord) -> str | None:
        parsed = urlparse(doc.raw_path)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return "url"
        suffix = Path(doc.source_name).suffix.lower().lstrip(".")
        if suffix in {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}:
            return "image"
        return suffix or None

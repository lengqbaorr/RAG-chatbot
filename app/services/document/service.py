from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from app.core.exceptions import BadRequestError, DocumentNotFoundError, VectorStoreAppError
from app.services.document.models import (
    DocumentChunkPreview,
    DocumentDeleteReport,
    DocumentInfo,
    DocumentPreview,
    DocumentRecord,
)
from app.services.document.repository import DocumentRepository
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.vectorstore.interfaces import BaseVectorStore

MAX_PREVIEW_CHARACTERS = 500_000


class DocumentService:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        vector_store: BaseVectorStore,
        loader: DocumentLoaderService | None = None,
    ) -> None:
        self.repository = repository
        self.vector_store = vector_store
        self.loader = loader or DocumentLoaderService()

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

    def get_preview(self, source_id: str) -> DocumentPreview:
        document = self.get_record(source_id)
        source_type = self._resolved_source_type(document)
        if source_type == "pdf":
            return DocumentPreview(
                source_id=source_id,
                source_name=document.source_name,
                source_type=source_type,
                mime_type="application/pdf",
                preview_kind="pdf",
                page_count=document.page_count,
            )

        content = self._stored_chunk_content(source_id)
        if not content:
            try:
                loaded = self.loader.load(LoaderInput(source=document.raw_path))
            except Exception as exc:
                raise BadRequestError("Document preview could not be generated") from exc
            content = "\n\n".join(doc.text for doc in loaded if doc.text.strip())
        truncated = len(content) > MAX_PREVIEW_CHARACTERS
        return DocumentPreview(
            source_id=source_id,
            source_name=document.source_name,
            source_type=source_type,
            mime_type=document.mime_type,
            preview_kind="text",
            page_count=document.page_count,
            content=content[:MAX_PREVIEW_CHARACTERS],
            truncated=truncated,
        )

    def get_chunk_preview(self, source_id: str, chunk_id: str) -> DocumentChunkPreview:
        self.get_record(source_id)
        record = self.vector_store.get_by_chunk_id(chunk_id)
        if record is None or record.source_id != source_id:
            raise DocumentNotFoundError(f"Chunk not found: {chunk_id}")
        return DocumentChunkPreview(
            chunk_id=record.chunk_id,
            source_id=record.source_id,
            content=record.content,
            page_start=record.page_start,
            page_end=record.page_end,
            section_title=record.section_title,
            metadata=record.metadata,
        )

    def get_preview_file(self, source_id: str) -> tuple[Path | None, str | None, str]:
        document = self.get_record(source_id)
        if self._resolved_source_type(document) != "pdf":
            raise BadRequestError("Raw file preview is only available for PDF documents")
        parsed = urlparse(document.raw_path)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return None, document.raw_path, document.source_name
        path = Path(document.raw_path).resolve()
        if not path.exists() or not path.is_file():
            raise DocumentNotFoundError("Raw document file was not found")
        return path, None, document.source_name

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

    def _resolved_source_type(self, doc: DocumentRecord) -> str:
        media_type = (doc.mime_type or "").split(";", maxsplit=1)[0].lower()
        if media_type == "application/pdf":
            return "pdf"
        suffix = Path(urlparse(doc.raw_path).path).suffix.lower()
        if suffix == ".pdf" or Path(doc.source_name).suffix.lower() == ".pdf":
            return "pdf"
        for chunk in self.repository.list_chunks(doc.source_id):
            record = self.vector_store.get_by_chunk_id(chunk.chunk_id)
            if record is not None and record.source_type:
                return record.source_type
        return self._source_type(doc) or "unknown"

    def _stored_chunk_content(self, source_id: str) -> str:
        chunks = self.repository.list_chunks(source_id)
        child_content = [
            chunk.content.strip()
            for chunk in chunks
            if chunk.content.strip() and chunk.parent_id is not None
        ]
        return "\n\n".join(child_content)

    @staticmethod
    def _source_type(doc: DocumentRecord) -> str | None:
        parsed = urlparse(doc.raw_path)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return "url"
        suffix = Path(doc.source_name).suffix.lower().lstrip(".")
        if suffix in {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}:
            return "image"
        return suffix or None

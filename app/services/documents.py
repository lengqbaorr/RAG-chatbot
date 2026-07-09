from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import DocumentNotFoundError, VectorStoreAppError
from app.services.vectorstore.interfaces import BaseVectorStore


@dataclass(frozen=True)
class DocumentInfo:
    source_id: str
    source_name: str
    source_type: str | None
    chunk_count: int


@dataclass(frozen=True)
class DocumentDeleteReport:
    source_id: str
    deleted_count: int


class DocumentManagementService:
    def __init__(self, *, vector_store: BaseVectorStore) -> None:
        self.vector_store = vector_store

    def list_documents(self) -> list[DocumentInfo]:
        records = self._get_all_metadata()
        grouped: dict[str, DocumentInfo] = {}
        counts: dict[str, int] = {}
        for meta in records:
            source_id = meta.get("source_id") or ""
            if not source_id:
                continue
            counts[source_id] = counts.get(source_id, 0) + 1
            grouped[source_id] = DocumentInfo(
                source_id=source_id,
                source_name=meta.get("source_name", ""),
                source_type=meta.get("source_type"),
                chunk_count=counts[source_id],
            )
        return list(grouped.values())

    def get_document(self, source_id: str) -> DocumentInfo:
        docs = [doc for doc in self.list_documents() if doc.source_id == source_id]
        if not docs:
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return docs[0]

    def delete_document(self, source_id: str) -> DocumentDeleteReport:
        try:
            result = self.vector_store.delete_by_source_id(source_id)
        except Exception as exc:
            raise VectorStoreAppError("Vector store delete failed") from exc
        if result.deleted_count == 0:
            raise DocumentNotFoundError(f"Document not found: {source_id}")
        return DocumentDeleteReport(source_id=source_id, deleted_count=result.deleted_count)

    def _get_all_metadata(self) -> list[dict]:
        collection = getattr(self.vector_store, "_collection", None)
        if collection is None:
            return []
        try:
            result = collection.get(include=["metadatas"])
        except Exception as exc:
            raise VectorStoreAppError("Vector store metadata scan failed") from exc
        return result.get("metadatas", []) or []

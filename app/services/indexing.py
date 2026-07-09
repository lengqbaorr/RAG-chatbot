from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import BadRequestError, DocumentLoadAppError, EmbeddingAppError, VectorStoreAppError
from app.services.chunking import ChunkingConfig, DocumentChunker
from app.services.chunking.hashers import stable_hash
from app.services.embedding import EmbeddingService
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.vectorstore.service import VectorStoreService


@dataclass(frozen=True)
class IndexingConfig:
    upload_dir: str = "./data/raw"
    max_upload_mb: int = 50
    allowed_extensions: tuple[str, ...] = ("pdf", "docx", "txt", "md")


@dataclass(frozen=True)
class IndexingReport:
    source_id: str
    source_name: str
    documents: int
    chunks: int
    embedded: int
    upserted: int
    excluded: int
    collection: str


class IndexingService:
    def __init__(
        self,
        *,
        loader: DocumentLoaderService,
        chunker: DocumentChunker,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
        config: IndexingConfig | None = None,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store_service = vector_store_service
        self.config = config or IndexingConfig()

    def index_upload(self, *, filename: str, file_obj: BinaryIO) -> IndexingReport:
        safe_name = self._safe_filename(filename)
        extension = self._extension(safe_name)
        if extension not in self.config.allowed_extensions:
            raise BadRequestError(
                f"Unsupported file extension: .{extension}",
                details={"allowed_extensions": list(self.config.allowed_extensions)},
            )

        raw_source_id = uuid.uuid4().hex
        source_id = stable_hash(None, raw_source_id)
        target_dir = Path(self.config.upload_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{raw_source_id}_{safe_name}"
        self._save_with_limit(file_obj, target_path)

        try:
            docs = self.loader.load(LoaderInput(source=str(target_path)))
        except Exception as exc:
            raise DocumentLoadAppError(f"Could not load document: {safe_name}") from exc

        docs = [
            doc.model_copy(
                update={
                    "metadata": doc.metadata.model_copy(
                        update={
                            "source": raw_source_id,
                            "title": safe_name,
                        }
                    )
                }
            )
            for doc in docs
        ]

        try:
            chunks = self.chunker.chunk_documents(docs)
        except Exception as exc:
            raise DocumentLoadAppError(f"Could not chunk document: {safe_name}") from exc

        try:
            embedded = self.embedding_service.embed_chunks(chunks)
        except Exception as exc:
            raise EmbeddingAppError("Embedding service failed") from exc

        try:
            upsert = self.vector_store_service.upsert_embeddings(embedded.chunks)
        except Exception as exc:
            raise VectorStoreAppError("Vector store upsert failed") from exc

        return IndexingReport(
            source_id=source_id,
            source_name=safe_name,
            documents=len(docs),
            chunks=len(chunks),
            embedded=embedded.report.embedded_count,
            upserted=upsert.upserted_count,
            excluded=embedded.report.excluded_chunks,
            collection=upsert.collection_name,
        )

    def _save_with_limit(self, file_obj: BinaryIO, target_path: Path) -> None:
        max_bytes = self.config.max_upload_mb * 1024 * 1024
        written = 0
        too_large = False
        with target_path.open("wb") as out:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    too_large = True
                    break
                out.write(chunk)

        if too_large:
            self._safe_unlink(target_path)
            raise BadRequestError(
                "Uploaded file is too large",
                details={"max_upload_mb": self.config.max_upload_mb},
            )

        if written == 0:
            self._safe_unlink(target_path)
            raise BadRequestError("Uploaded file is empty")

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip()
        name = re.sub(r"[^A-Za-z0-9._ -]", "_", name)
        name = name.replace("..", "_")
        if not name:
            raise BadRequestError("Invalid filename")
        return name

    def _extension(self, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if not suffix:
            raise BadRequestError("Uploaded file must have an extension")
        return suffix

    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except PermissionError:
            pass

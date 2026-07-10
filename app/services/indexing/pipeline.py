from __future__ import annotations

import logging
from pathlib import Path

from app.core.exceptions import DocumentLoadAppError, EmbeddingAppError, VectorStoreAppError
from app.schemas.chunk import DocumentChunk
from app.services.chunking import DocumentChunker
from app.services.document.models import ChunkRecord, DocumentStatus
from app.services.document.repository import DocumentRepository
from app.services.embedding import EmbeddingService
from app.services.indexing.models import IndexingReport
from app.services.ingestion import DocumentLoaderService, LoaderInput
from app.services.jobs.models import JobStage
from app.services.jobs.service import JobService
from app.services.vectorstore.service import VectorStoreService

logger = logging.getLogger(__name__)


class IndexingPipeline:
    def __init__(
        self,
        *,
        loader: DocumentLoaderService,
        chunker: DocumentChunker,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
        document_repository: DocumentRepository,
        job_service: JobService,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.vector_store_service = vector_store_service
        self.document_repository = document_repository
        self.job_service = job_service

    def run(self, *, job_id: str, source_id: str) -> IndexingReport:
        document = self.document_repository.get_document(source_id)
        if document is None:
            raise DocumentLoadAppError(f"Document not found for indexing: {source_id}")

        self.job_service.mark_running(job_id, stage=JobStage.loading, progress=15)
        self.document_repository.update_document(source_id, status=DocumentStatus.indexing)
        try:
            docs = self.loader.load(LoaderInput(source=document.raw_path))
        except Exception as exc:
            raise DocumentLoadAppError(f"Could not load document: {document.source_name}") from exc

        docs = [
            doc.model_copy(
                update={
                    "metadata": doc.metadata.model_copy(
                        update={
                            "source": source_id,
                            "title": document.source_name,
                        }
                    )
                }
            )
            for doc in docs
        ]

        self.job_service.update_progress(job_id, stage=JobStage.chunking, progress=40)
        try:
            chunks = self.chunker.chunk_documents(docs)
        except Exception as exc:
            raise DocumentLoadAppError(f"Could not chunk document: {document.source_name}") from exc
        chunks = self._assign_platform_source_id(chunks, source_id)

        self.document_repository.replace_chunks(
            source_id,
            [
                ChunkRecord(
                    chunk_id=chunk.chunk_id,
                    source_id=source_id,
                    parent_id=chunk.metadata.parent_id,
                    page_start=chunk.metadata.page_start,
                    page_end=chunk.metadata.page_end,
                    section_title=chunk.metadata.section_title,
                    header_path=chunk.metadata.header_path,
                    token_count=chunk.token_count,
                    retrieval_excluded=chunk.metadata.retrieval_excluded,
                    content_hash=chunk.content_hash,
                )
                for chunk in chunks
            ],
        )

        self.job_service.update_progress(job_id, stage=JobStage.embedding, progress=70)
        try:
            embedded = self.embedding_service.embed_chunks(chunks)
        except Exception as exc:
            raise EmbeddingAppError("Embedding service failed") from exc

        self.job_service.update_progress(job_id, stage=JobStage.vectorstore, progress=90)
        try:
            upsert = self.vector_store_service.upsert_embeddings(embedded.chunks)
        except Exception as exc:
            raise VectorStoreAppError("Vector store upsert failed") from exc

        language = next((chunk.metadata.language for chunk in chunks if chunk.metadata.language), None)
        page_count = max((doc.metadata.page_number or 0 for doc in docs), default=len(docs))
        self.document_repository.update_document(
            source_id,
            status=DocumentStatus.completed,
            language=language,
            page_count=page_count,
            chunk_count=len(chunks),
            embedding_model=embedded.report.model_name,
            embedding_dimension=embedded.report.dimension,
            collection_name=upsert.collection_name,
        )
        self.job_service.mark_completed(job_id)

        logger.info(
            "indexing_completed",
            extra={"job_id": job_id, "source_id": source_id, "chunks": len(chunks)},
        )
        return IndexingReport(
            source_id=source_id,
            source_name=document.source_name,
            documents=len(docs),
            chunks=len(chunks),
            embedded=embedded.report.embedded_count,
            upserted=upsert.upserted_count,
            excluded=embedded.report.excluded_chunks,
            collection=upsert.collection_name,
        )

    @staticmethod
    def _assign_platform_source_id(
        chunks: list[DocumentChunk],
        source_id: str,
    ) -> list[DocumentChunk]:
        return [
            chunk.model_copy(
                update={
                    "source_id": source_id,
                    "document_id": source_id,
                    "metadata": chunk.metadata.model_copy(
                        update={"source_id": source_id}
                    ),
                }
            )
            for chunk in chunks
        ]

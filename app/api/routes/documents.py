from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.dependencies import get_document_service, get_indexing_service
from app.api.schemas.documents import (
    DocumentDeleteResponse,
    DocumentInfoResponse,
    DocumentListResponse,
    DocumentUrlUploadRequest,
    DocumentUploadResponse,
)
from app.services.document import DocumentService
from app.services.indexing import IndexingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> DocumentUploadResponse:
    if hasattr(indexing_service, "submit_upload"):
        submission = indexing_service.submit_upload(
            filename=file.filename or "",
            file_obj=file.file,
            mime_type=file.content_type,
        )
        response_data = submission.__dict__
    else:
        report = indexing_service.index_upload(filename=file.filename or "", file_obj=file.file)
        response_data = {
            "job_id": None,
            "source_id": report.source_id,
            "status": "COMPLETED",
            "duplicate": False,
            "source_name": report.source_name,
            "documents": report.documents,
            "chunks": report.chunks,
            "embedded": report.embedded,
            "upserted": report.upserted,
            "excluded": report.excluded,
            "collection": report.collection,
        }
    logger.info(
        "document_upload_submitted",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "source_id": response_data["source_id"],
            "job_id": response_data["job_id"],
        },
    )
    return DocumentUploadResponse(**response_data)


@router.post("/url", response_model=DocumentUploadResponse)
def upload_url(
    payload: DocumentUrlUploadRequest,
    request: Request,
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> DocumentUploadResponse:
    submission = indexing_service.submit_url(url=payload.url, title=payload.title)
    logger.info(
        "document_url_submitted",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "source_id": submission.source_id,
            "job_id": submission.job_id,
        },
    )
    return DocumentUploadResponse(**submission.__dict__)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    return DocumentListResponse(
        documents=[DocumentInfoResponse(**doc.__dict__) for doc in document_service.list_documents()]
    )


@router.get("/{source_id}", response_model=DocumentInfoResponse)
def get_document(
    source_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentInfoResponse:
    doc = document_service.get_document(source_id)
    return DocumentInfoResponse(**doc.__dict__)


@router.delete("/{source_id}", response_model=DocumentDeleteResponse)
def delete_document(
    source_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    report = document_service.delete_document(source_id)
    deleted_vectors = getattr(report, "deleted_vectors", getattr(report, "deleted_count", 0))
    deleted_chunks = getattr(report, "deleted_chunks", deleted_vectors)
    return DocumentDeleteResponse(
        source_id=report.source_id,
        deleted_count=deleted_vectors,
        deleted_vectors=deleted_vectors,
        deleted_chunks=deleted_chunks,
        raw_file_deleted=getattr(report, "raw_file_deleted", False),
    )


@router.post("/reindex/{source_id}", response_model=DocumentUploadResponse)
def reindex_document(
    source_id: str,
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> DocumentUploadResponse:
    submission = indexing_service.submit_reindex(source_id)
    return DocumentUploadResponse(**submission.__dict__)

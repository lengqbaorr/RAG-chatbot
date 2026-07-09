from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.dependencies import get_document_service, get_indexing_service
from app.api.schemas.documents import (
    DocumentDeleteResponse,
    DocumentInfoResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.documents import DocumentManagementService
from app.services.indexing import IndexingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents")


@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    request: Request,
    file: UploadFile = File(...),
    indexing_service: IndexingService = Depends(get_indexing_service),
) -> DocumentUploadResponse:
    report = indexing_service.index_upload(filename=file.filename or "", file_obj=file.file)
    logger.info(
        "document_uploaded",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "source_id": report.source_id,
            "source_name": report.source_name,
        },
    )
    return DocumentUploadResponse(**report.__dict__)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    document_service: DocumentManagementService = Depends(get_document_service),
) -> DocumentListResponse:
    return DocumentListResponse(
        documents=[DocumentInfoResponse(**doc.__dict__) for doc in document_service.list_documents()]
    )


@router.get("/{source_id}", response_model=DocumentInfoResponse)
def get_document(
    source_id: str,
    document_service: DocumentManagementService = Depends(get_document_service),
) -> DocumentInfoResponse:
    doc = document_service.get_document(source_id)
    return DocumentInfoResponse(**doc.__dict__)


@router.delete("/{source_id}", response_model=DocumentDeleteResponse)
def delete_document(
    source_id: str,
    document_service: DocumentManagementService = Depends(get_document_service),
) -> DocumentDeleteResponse:
    report = document_service.delete_document(source_id)
    return DocumentDeleteResponse(**report.__dict__)

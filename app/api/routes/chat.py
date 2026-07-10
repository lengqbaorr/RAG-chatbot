from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_rag_pipeline
from app.api.schemas.chat import ChatReportResponse, ChatRequest, ChatResponse, SourceCitationResponse
from app.core.exceptions import AppError, RetrievalAppError
from app.services.rag import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    document_service = getattr(request.app.state, "document_service", None)
    if document_service is not None and hasattr(document_service, "completed_source_ids"):
        filters = _completed_document_filters(payload.filters, document_service.completed_source_ids())
    else:
        filters = payload.filters
    try:
        result = rag_pipeline.answer(
            payload.question,
            strategy=payload.strategy,
            filters=filters,
            top_k=payload.top_k,
            fetch_k=payload.fetch_k,
            min_score=payload.min_score,
        )
    except AppError:
        raise
    except Exception as exc:
        logger.exception(
            "chat_pipeline_failed",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "question_preview": payload.question[:120],
                "retrieval_strategy": payload.strategy,
            },
        )
        raise RetrievalAppError("RAG pipeline failed") from exc

    logger.info(
        "chat_completed",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "question_preview": payload.question[:120],
            "retrieval_strategy": payload.strategy,
            "sources": len(result.sources),
        },
    )

    return ChatResponse(
        answer=result.answer,
        sources=[
            SourceCitationResponse(
                source_id=source.source_id,
                source_name=source.source_name,
                page_start=source.page_start,
                page_end=source.page_end,
                section_title=source.section_title,
                chunk_id=source.chunk_id,
                score=source.score,
                content_preview=source.content_preview,
            )
            for source in result.sources
        ],
        report=ChatReportResponse(
            retrieval_strategy=result.retrieval_report.strategy,
            retrieval_results=result.retrieval_report.final_results,
            context_sources=result.report.context_sources,
            llm_provider=result.llm_provider,
            llm_model=result.llm_model,
            llm_finish_reason=result.report.llm_finish_reason,
            llm_prompt_tokens=result.report.llm_prompt_tokens,
            llm_completion_tokens=result.report.llm_completion_tokens,
            llm_total_tokens=result.report.llm_total_tokens,
            total_latency=result.latency,
        ),
    )


def _completed_document_filters(filters: dict | None, completed_source_ids: list[str]) -> dict:
    merged = dict(filters or {})
    completed = set(completed_source_ids)
    if "source_id" in merged:
        requested = merged["source_id"]
        if isinstance(requested, dict) and "$in" in requested:
            allowed = [sid for sid in requested["$in"] if sid in completed]
        else:
            allowed = [requested] if requested in completed else []
        merged["source_id"] = {"$in": allowed or ["__no_completed_document__"]}
        return merged
    merged["source_id"] = {"$in": list(completed) or ["__no_completed_document__"]}
    return merged

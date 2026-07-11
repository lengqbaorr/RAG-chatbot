from __future__ import annotations

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_history_service, get_rag_pipeline
from app.api.schemas.chat import ChatReportResponse, ChatRequest, ChatResponse, SourceCitationResponse
from app.core.exceptions import AppError, RetrievalAppError
from app.services.chat_history import (
    ChatHistoryService,
    ChatMessageStatus,
    ChatRole,
)
from app.services.rag import RAGAnswer, RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    chat_history: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatResponse:
    session_id, selected_source_ids = _prepare_history(payload, chat_history)
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
        chat_history.add_message(
            session_id=session_id,
            role=ChatRole.assistant,
            content="RAG pipeline failed",
            selected_source_ids=selected_source_ids,
            status=ChatMessageStatus.failed,
        )
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

    response = _to_chat_response(result, session_id=session_id)
    _save_assistant_message(response, selected_source_ids, chat_history)
    return response


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    request: Request,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    chat_history: ChatHistoryService = Depends(get_chat_history_service),
) -> StreamingResponse:
    session_id, selected_source_ids = _prepare_history(payload, chat_history)
    document_service = getattr(request.app.state, "document_service", None)
    if document_service is not None and hasattr(document_service, "completed_source_ids"):
        filters = _completed_document_filters(payload.filters, document_service.completed_source_ids())
    else:
        filters = payload.filters

    def event_stream() -> Iterator[str]:
        answer_parts: list[str] = []
        persisted = False
        stream = rag_pipeline.stream(
            payload.question,
            strategy=payload.strategy,
            filters=filters,
            top_k=payload.top_k,
            fetch_k=payload.fetch_k,
            min_score=payload.min_score,
        )
        try:
            for event in stream:
                if event.event == "start":
                    yield _encode_sse(
                        "start",
                        {"status": "streaming", "session_id": session_id},
                    )
                elif event.event == "delta":
                    text = event.text or ""
                    answer_parts.append(text)
                    yield _encode_sse("delta", {"text": text})
                elif event.event == "complete" and event.answer is not None:
                    response = _to_chat_response(event.answer, session_id=session_id)
                    _save_assistant_message(response, selected_source_ids, chat_history)
                    persisted = True
                    yield _encode_sse("complete", response.model_dump(mode="json"))
                    logger.info(
                        "chat_stream_completed",
                        extra={
                            "request_id": getattr(request.state, "request_id", None),
                            "question_preview": payload.question[:120],
                            "retrieval_strategy": payload.strategy,
                            "sources": len(event.answer.sources),
                        },
                    )
        except GeneratorExit:
            if not persisted and answer_parts:
                chat_history.add_message(
                    session_id=session_id,
                    role=ChatRole.assistant,
                    content="".join(answer_parts),
                    selected_source_ids=selected_source_ids,
                    status=ChatMessageStatus.cancelled,
                )
            logger.info(
                "chat_stream_cancelled",
                extra={"request_id": getattr(request.state, "request_id", None)},
            )
            raise
        except Exception:
            if not persisted:
                chat_history.add_message(
                    session_id=session_id,
                    role=ChatRole.assistant,
                    content="".join(answer_parts) or "RAG streaming failed",
                    selected_source_ids=selected_source_ids,
                    status=ChatMessageStatus.failed,
                )
            logger.exception(
                "chat_stream_failed",
                extra={
                    "request_id": getattr(request.state, "request_id", None),
                    "question_preview": payload.question[:120],
                    "retrieval_strategy": payload.strategy,
                },
            )
            yield _encode_sse(
                "error",
                {"code": "rag_stream_error", "message": "RAG streaming failed"},
            )
        finally:
            close = getattr(stream, "close", None)
            if close is not None:
                close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _to_chat_response(result: RAGAnswer, *, session_id: str | None = None) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
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


def _encode_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _prepare_history(
    payload: ChatRequest,
    service: ChatHistoryService,
) -> tuple[str, list[str]]:
    selected_source_ids = _selected_source_ids(payload)
    if payload.session_id:
        session = service.get_session(payload.session_id)
        if not selected_source_ids:
            selected_source_ids = session.selected_source_ids
        service.update_session(
            session.session_id,
            selected_source_ids=selected_source_ids,
        )
    else:
        session = service.create_session(
            title=service.title_from_question(payload.question),
            selected_source_ids=selected_source_ids,
        )
    service.add_message(
        session_id=session.session_id,
        role=ChatRole.user,
        content=payload.question,
        selected_source_ids=selected_source_ids,
    )
    return session.session_id, selected_source_ids


def _selected_source_ids(payload: ChatRequest) -> list[str]:
    if payload.selected_source_ids:
        return list(dict.fromkeys(payload.selected_source_ids))
    source_filter = (payload.filters or {}).get("source_id")
    if isinstance(source_filter, str):
        return [source_filter]
    if isinstance(source_filter, dict) and isinstance(source_filter.get("$in"), list):
        return [str(source_id) for source_id in source_filter["$in"]]
    return []


def _save_assistant_message(
    response: ChatResponse,
    selected_source_ids: list[str],
    service: ChatHistoryService,
) -> None:
    if response.session_id is None:
        return
    service.add_message(
        session_id=response.session_id,
        role=ChatRole.assistant,
        content=response.answer,
        sources=[source.model_dump(mode="json") for source in response.sources],
        selected_source_ids=selected_source_ids,
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

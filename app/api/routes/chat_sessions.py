from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_chat_history_service
from app.api.schemas.chat import (
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDeleteResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdateRequest,
    SourceCitationResponse,
)
from app.services.chat_history import ChatHistoryService

router = APIRouter(prefix="/chat/sessions")


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreateRequest,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionResponse:
    return _session_response(
        service.create_session(
            title=payload.title,
            selected_source_ids=payload.selected_source_ids,
        )
    )


@router.get("", response_model=ChatSessionListResponse)
def list_sessions(
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionListResponse:
    return ChatSessionListResponse(
        sessions=[_session_response(session) for session in service.list_sessions()]
    )


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
def get_session(
    session_id: str,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionDetailResponse:
    detail = service.get_detail(session_id)
    return ChatSessionDetailResponse(
        session=_session_response(detail.session),
        messages=[_message_response(message) for message in detail.messages],
    )


@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
def list_messages(
    session_id: str,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> list[ChatMessageResponse]:
    detail = service.get_detail(session_id)
    return [_message_response(message) for message in detail.messages]


@router.patch("/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: str,
    payload: ChatSessionUpdateRequest,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionResponse:
    return _session_response(
        service.update_session(
            session_id,
            title=payload.title,
            selected_source_ids=payload.selected_source_ids,
        )
    )


@router.delete("/{session_id}", response_model=ChatSessionDeleteResponse)
def delete_session(
    session_id: str,
    service: ChatHistoryService = Depends(get_chat_history_service),
) -> ChatSessionDeleteResponse:
    service.delete_session(session_id)
    return ChatSessionDeleteResponse(session_id=session_id)


def _session_response(session) -> ChatSessionResponse:
    return ChatSessionResponse(
        session_id=session.session_id,
        title=session.title,
        selected_source_ids=session.selected_source_ids,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _message_response(message) -> ChatMessageResponse:
    return ChatMessageResponse(
        message_id=message.message_id,
        session_id=message.session_id,
        role=message.role.value,
        content=message.content,
        sources=[SourceCitationResponse.model_validate(source) for source in message.sources],
        selected_source_ids=message.selected_source_ids,
        status=message.status.value,
        timestamp=message.timestamp,
    )

from __future__ import annotations

import uuid

from app.core.exceptions import ChatSessionNotFoundError
from app.services.chat_history.models import (
    ChatMessageRecord,
    ChatMessageStatus,
    ChatRole,
    ChatSessionDetail,
    ChatSessionRecord,
)
from app.services.chat_history.repository import ChatHistoryRepository


class ChatHistoryService:
    def __init__(self, repository: ChatHistoryRepository) -> None:
        self.repository = repository

    def create_session(
        self,
        *,
        title: str = "New chat",
        owner: str | None = None,
        selected_source_ids: list[str] | None = None,
    ) -> ChatSessionRecord:
        return self.repository.create_session(
            session_id=uuid.uuid4().hex,
            title=self._clean_title(title),
            owner=owner,
            selected_source_ids=self._unique_ids(selected_source_ids or []),
        )

    def get_session(self, session_id: str) -> ChatSessionRecord:
        session = self.repository.get_session(session_id)
        if session is None:
            raise ChatSessionNotFoundError(f"Chat session not found: {session_id}")
        return session

    def get_detail(self, session_id: str) -> ChatSessionDetail:
        return ChatSessionDetail(
            session=self.get_session(session_id),
            messages=self.repository.list_messages(session_id),
        )

    def list_sessions(self, *, owner: str | None = None) -> list[ChatSessionRecord]:
        return self.repository.list_sessions(owner=owner)

    def update_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        selected_source_ids: list[str] | None = None,
    ) -> ChatSessionRecord:
        self.get_session(session_id)
        updated = self.repository.update_session(
            session_id,
            title=self._clean_title(title) if title is not None else None,
            selected_source_ids=(
                self._unique_ids(selected_source_ids)
                if selected_source_ids is not None
                else None
            ),
        )
        if updated is None:
            raise ChatSessionNotFoundError(f"Chat session not found: {session_id}")
        return updated

    def delete_session(self, session_id: str) -> None:
        if not self.repository.delete_session(session_id):
            raise ChatSessionNotFoundError(f"Chat session not found: {session_id}")

    def add_message(
        self,
        *,
        session_id: str,
        role: ChatRole,
        content: str,
        sources: list[dict] | None = None,
        selected_source_ids: list[str] | None = None,
        status: ChatMessageStatus = ChatMessageStatus.completed,
    ) -> ChatMessageRecord:
        self.get_session(session_id)
        selected = self._unique_ids(selected_source_ids or [])
        message = self.repository.add_message(
            message_id=uuid.uuid4().hex,
            session_id=session_id,
            role=role,
            content=content,
            sources=sources,
            selected_source_ids=selected,
            status=status,
        )
        if selected:
            self.repository.update_session(
                session_id,
                selected_source_ids=selected,
            )
        return message

    @staticmethod
    def title_from_question(question: str) -> str:
        return ChatHistoryService._clean_title(question)

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = " ".join(title.split()).strip()
        return (cleaned or "New chat")[:120]

    @staticmethod
    def _unique_ids(source_ids: list[str]) -> list[str]:
        return list(dict.fromkeys(source_id for source_id in source_ids if source_id))

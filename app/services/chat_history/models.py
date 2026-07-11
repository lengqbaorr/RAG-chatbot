from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ChatRole(StrEnum):
    user = "user"
    assistant = "assistant"


class ChatMessageStatus(StrEnum):
    completed = "completed"
    cancelled = "cancelled"
    failed = "failed"


@dataclass(frozen=True)
class ChatSessionRecord:
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    owner: str | None = None
    selected_source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChatMessageRecord:
    message_id: str
    session_id: str
    role: ChatRole
    content: str
    timestamp: datetime
    sources: list[dict[str, Any]] = field(default_factory=list)
    selected_source_ids: list[str] = field(default_factory=list)
    status: ChatMessageStatus = ChatMessageStatus.completed


@dataclass(frozen=True)
class ChatSessionDetail:
    session: ChatSessionRecord
    messages: list[ChatMessageRecord] = field(default_factory=list)

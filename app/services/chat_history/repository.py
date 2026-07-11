from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from app.db import Database
from app.services.chat_history.models import (
    ChatMessageRecord,
    ChatMessageStatus,
    ChatRole,
    ChatSessionRecord,
)


class ChatHistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_session(
        self,
        *,
        session_id: str,
        title: str,
        owner: str | None = None,
        selected_source_ids: list[str] | None = None,
    ) -> ChatSessionRecord:
        now = datetime.utcnow().isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, title, owner, selected_source_ids, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    title,
                    owner,
                    json.dumps(selected_source_ids or []),
                    now,
                    now,
                ),
            )
        session = self.get_session(session_id)
        if session is None:
            raise RuntimeError("chat session insert failed")
        return session

    def get_session(self, session_id: str) -> ChatSessionRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(self, *, owner: str | None = None) -> list[ChatSessionRecord]:
        sql = "SELECT * FROM chat_sessions"
        params: tuple[object, ...] = ()
        if owner is not None:
            sql += " WHERE owner = ?"
            params = (owner,)
        sql += " ORDER BY updated_at DESC"
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_session(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        *,
        title: str | None = None,
        selected_source_ids: list[str] | None = None,
    ) -> ChatSessionRecord | None:
        fields: dict[str, object] = {"updated_at": datetime.utcnow().isoformat()}
        if title is not None:
            fields["title"] = title
        if selected_source_ids is not None:
            fields["selected_source_ids"] = json.dumps(selected_source_ids)
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = [*fields.values(), session_id]
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE chat_sessions SET {assignments} WHERE session_id = ?",
                values,
            )
        return self.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            )
        return cursor.rowcount > 0

    def add_message(
        self,
        *,
        message_id: str,
        session_id: str,
        role: ChatRole,
        content: str,
        sources: list[dict] | None = None,
        selected_source_ids: list[str] | None = None,
        status: ChatMessageStatus = ChatMessageStatus.completed,
    ) -> ChatMessageRecord:
        now = datetime.utcnow().isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (
                    message_id, session_id, role, content, sources,
                    selected_source_ids, status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role.value,
                    content,
                    json.dumps(sources or [], ensure_ascii=False),
                    json.dumps(selected_source_ids or []),
                    status.value,
                    now,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
        message = self.get_message(message_id)
        if message is None:
            raise RuntimeError("chat message insert failed")
        return message

    def get_message(self, message_id: str) -> ChatMessageRecord | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM chat_messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()
        return self._row_to_message(row) if row else None

    def list_messages(self, session_id: str) -> list[ChatMessageRecord]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC, message_id ASC
                """,
                (session_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> ChatSessionRecord:
        return ChatSessionRecord(
            session_id=row["session_id"],
            title=row["title"],
            owner=row["owner"],
            selected_source_ids=json.loads(row["selected_source_ids"] or "[]"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> ChatMessageRecord:
        return ChatMessageRecord(
            message_id=row["message_id"],
            session_id=row["session_id"],
            role=ChatRole(row["role"]),
            content=row["content"],
            sources=json.loads(row["sources"] or "[]"),
            selected_source_ids=json.loads(row["selected_source_ids"] or "[]"),
            status=ChatMessageStatus(row["status"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )

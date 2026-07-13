from __future__ import annotations

from app.db import Database
from app.services.chat_history import ChatHistoryRepository, ChatHistoryService, ChatRole
from app.services.conversation import ConversationContextService


def test_resolve_follow_up_question_with_previous_user_anchor(tmp_path) -> None:
    database = Database(str(tmp_path / "conversation.db"))
    database.initialize()
    history = ChatHistoryService(ChatHistoryRepository(database))
    session = history.create_session(title="VSM")
    history.add_message(
        session_id=session.session_id,
        role=ChatRole.user,
        content="Vector Space Model là gì?",
    )
    history.add_message(
        session_id=session.session_id,
        role=ChatRole.assistant,
        content="Vector Space Model biểu diễn tài liệu dưới dạng vector.",
    )

    resolved = ConversationContextService(history).resolve_question(
        session_id=session.session_id,
        question="Nó khác BM25 thế nào?",
    )

    assert resolved.rewritten is True
    assert resolved.original_question == "Nó khác BM25 thế nào?"
    assert "Vector Space Model là gì" in resolved.retrieval_query
    assert resolved.conversation.used_messages == 2


def test_standalone_question_is_not_rewritten_without_context(tmp_path) -> None:
    database = Database(str(tmp_path / "conversation.db"))
    database.initialize()
    history = ChatHistoryService(ChatHistoryRepository(database))
    session = history.create_session(title="Empty")

    resolved = ConversationContextService(history).resolve_question(
        session_id=session.session_id,
        question="Vector Space Model là gì?",
    )

    assert resolved.rewritten is False
    assert resolved.retrieval_query == "Vector Space Model là gì?"

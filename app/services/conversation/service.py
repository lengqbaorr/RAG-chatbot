from __future__ import annotations

import re

from app.services.chat_history import ChatHistoryService, ChatMessageStatus
from app.services.conversation.models import ConversationContext, ConversationTurn, ResolvedQuestion


FOLLOW_UP_PATTERNS = (
    r"\b(cái|loại|mô hình|phương pháp|thuật toán|nó|chúng|chúng nó|cái này|cái đó)\b",
    r"\b(tốt hơn|khác gì|ưu điểm|nhược điểm|so sánh|tiếp|vậy|thế nào|nên dùng)\b",
    r"\b(it|this|that|they|them|which|better|compare|pros|cons)\b",
)

STOP_PREFIXES = (
    "dựa trên",
    "theo tài liệu",
    "tóm lại",
    "nhìn chung",
    "câu trả lời",
)


class ConversationContextService:
    def __init__(
        self,
        chat_history: ChatHistoryService,
        *,
        max_turns: int = 6,
        max_message_characters: int = 700,
    ) -> None:
        self.chat_history = chat_history
        self.max_turns = max_turns
        self.max_message_characters = max_message_characters

    def resolve_question(self, *, session_id: str, question: str) -> ResolvedQuestion:
        context = self.build_context(session_id=session_id, exclude_latest_user_question=question)
        retrieval_query = self.rewrite(question=question, context=context)
        return ResolvedQuestion(
            original_question=question,
            retrieval_query=retrieval_query,
            conversation=context,
            rewritten=retrieval_query.strip() != question.strip(),
        )

    def build_context(
        self,
        *,
        session_id: str,
        exclude_latest_user_question: str | None = None,
    ) -> ConversationContext:
        messages = [
            message
            for message in self.chat_history.repository.list_messages(session_id)
            if message.status == ChatMessageStatus.completed and message.content.strip()
        ]
        if (
            exclude_latest_user_question is not None
            and messages
            and str(messages[-1].role) == "user"
            and self._normalize(messages[-1].content) == self._normalize(exclude_latest_user_question)
        ):
            messages = messages[:-1]
        turns = [
            ConversationTurn(
                role=str(message.role),
                content=self._trim(message.content),
            )
            for message in messages[-self.max_turns :]
        ]
        return ConversationContext(turns=turns)

    def rewrite(self, *, question: str, context: ConversationContext) -> str:
        cleaned_question = self._normalize(question)
        if not context.turns or not self._looks_like_follow_up(cleaned_question):
            return cleaned_question

        anchor = self._anchor_from_history(context)
        if not anchor:
            return cleaned_question

        return (
            "Dựa trên ngữ cảnh hội thoại trước đó về "
            f"{anchor}, hãy trả lời câu hỏi: {cleaned_question}"
        )

    def _anchor_from_history(self, context: ConversationContext) -> str:
        user_turns = [turn.content for turn in context.turns if turn.role == "user"]
        assistant_turns = [turn.content for turn in context.turns if turn.role == "assistant"]

        for candidate in reversed(user_turns):
            normalized = self._normalize(candidate)
            if normalized and not self._looks_like_follow_up(normalized):
                return self._strip_question_mark(normalized)

        if user_turns:
            return self._strip_question_mark(self._normalize(user_turns[-1]))

        if assistant_turns:
            return self._summary_anchor(assistant_turns[-1])
        return ""

    def _summary_anchor(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?。])\s+", self._normalize(text))
        for sentence in sentences:
            lower = sentence.lower()
            if sentence and not lower.startswith(STOP_PREFIXES):
                return self._strip_question_mark(sentence[:240])
        return self._strip_question_mark(self._normalize(text)[:240])

    def _looks_like_follow_up(self, question: str) -> bool:
        lower = question.lower()
        word_count = len(lower.split())
        if word_count <= 5:
            return True
        return any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in FOLLOW_UP_PATTERNS)

    def _trim(self, text: str) -> str:
        normalized = self._normalize(text)
        return normalized[: self.max_message_characters]

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.split()).strip()

    @staticmethod
    def _strip_question_mark(text: str) -> str:
        return text.rstrip(" ?.!。")

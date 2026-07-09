from __future__ import annotations

from app.services.llm.models import LLMMessage, LLMRequest
from app.services.rag.models import BuiltContext


DEFAULT_SYSTEM_PROMPT = """Bạn là trợ lý RAG trả lời dựa trên tài liệu được cung cấp.

Quy tắc:
1. Chỉ sử dụng thông tin trong CONTEXT.
2. Nếu CONTEXT không đủ thông tin, trả lời: "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."
3. Không bịa thêm thông tin ngoài tài liệu.
4. Trả lời bằng tiếng Việt.
5. Luôn trích dẫn nguồn theo dạng [Source n]."""


class PromptBuilder:
    def __init__(self, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> None:
        self.system_prompt = system_prompt

    def build(
        self,
        *,
        question: str,
        context: BuiltContext,
        conversation_history: list[LLMMessage] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMRequest:
        messages = [LLMMessage(role="system", content=self.system_prompt)]
        if conversation_history:
            messages.extend(conversation_history)

        user_content = (
            "CONTEXT:\n"
            f"{context.text or '(empty)'}\n\n"
            "QUESTION:\n"
            f"{question}\n\n"
            "ANSWER:"
        )
        messages.append(LLMMessage(role="user", content=user_content))
        return LLMRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata={
                "context_sources": len(context.sources),
                "context_tokens": context.token_count,
            },
        )

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str


@dataclass(frozen=True)
class ConversationContext:
    turns: list[ConversationTurn] = field(default_factory=list)

    @property
    def used_messages(self) -> int:
        return len(self.turns)


@dataclass(frozen=True)
class ResolvedQuestion:
    original_question: str
    retrieval_query: str
    conversation: ConversationContext
    rewritten: bool = False

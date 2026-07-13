from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBuilderConfig:
    max_context_tokens: int = 3000
    include_metadata: bool = True
    include_scores: bool = False
    deduplicate: bool = True


@dataclass(frozen=True)
class PromptBuilderConfig:
    answer_language: str = "vi"


@dataclass(frozen=True)
class RAGPipelineConfig:
    retrieval_strategy: str = "parent_child"
    top_k: int = 5
    fetch_k: int = 20
    min_score: float | None = None
    fallback_min_score: float = 0.55
    enable_empty_retrieval_fallback: bool = True
    call_llm_on_empty_context: bool = False
    empty_context_answer: str = "Tôi không tìm thấy thông tin này trong tài liệu được cung cấp."

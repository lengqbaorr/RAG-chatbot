from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationConfig:
    recall_ks: tuple[int, ...] = (1, 3, 5, 10)
    precision_k: int = 5
    citation_k: int = 5
    keyword_match_threshold: float = 0.5
    relevance_threshold: float = 0.5
    unanswerable_score_threshold: float = 0.55
    default_strategy: str = "parent_child"
    default_top_k: int = 5
    default_fetch_k: int = 20
    default_min_score: float = 0.0
    filters: dict | None = field(default=None)


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    strategy: str = "parent_child"
    top_k: int = 5
    fetch_k: int = 20
    min_score: float = 0.0
    filters: dict | None = None
    use_reranker: bool = False
    rerank_top_k: int = 5

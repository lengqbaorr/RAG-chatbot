from dataclasses import dataclass, field


@dataclass
class RetrievalConfig:
    strategy: str = "dense"
    top_k: int = 5
    fetch_k: int = 20
    min_score: float = 0.0
    filters: dict | None = None
    deduplicate_by: str = "chunk_id"
    exclude_content_types: tuple[str, ...] = ("cover", "toc")
    include_chunk_levels: tuple[str, ...] = ("child",)
    lowercase_query: bool = False
    remove_noisy_punctuation: bool = True

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k must be >= 1")
        if self.fetch_k < 1:
            raise ValueError("fetch_k must be >= 1")
        if self.fetch_k < self.top_k:
            self.fetch_k = self.top_k
        if self.min_score < 0.0 or self.min_score > 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")


@dataclass
class ParentChildRetrievalConfig(RetrievalConfig):
    strategy: str = "parent_child"
    child_fetch_k: int = 20
    parent_top_k: int = 5
    fallback_to_child: bool = True
    deduplicate_by: str = "parent_id"
    include_chunk_levels: tuple[str, ...] = ("child",)
    filters: dict | None = field(default_factory=lambda: {"chunk_level": "child"})

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.child_fetch_k < 1:
            raise ValueError("child_fetch_k must be >= 1")
        if self.parent_top_k < 1:
            raise ValueError("parent_top_k must be >= 1")
        if self.child_fetch_k < self.parent_top_k:
            self.child_fetch_k = self.parent_top_k
        self.fetch_k = self.child_fetch_k
        self.top_k = self.parent_top_k

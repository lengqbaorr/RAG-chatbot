from __future__ import annotations

from app.services.retrieval.models import RetrievedChunk


class ScoreThresholdFilter:
    def __init__(self, min_score: float = 0.0) -> None:
        if min_score < 0.0 or min_score > 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0")
        self.min_score = min_score

    def apply(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if self.min_score <= 0.0:
            return list(chunks)
        return [chunk for chunk in chunks if chunk.score >= self.min_score]


class ContentTypeFilter:
    def __init__(
        self,
        *,
        exclude_content_types: tuple[str, ...] = ("cover", "toc"),
        include_chunk_levels: tuple[str, ...] = ("child",),
    ) -> None:
        self.exclude_content_types = set(exclude_content_types)
        self.include_chunk_levels = set(include_chunk_levels)

    def apply(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        filtered: list[RetrievedChunk] = []
        for chunk in chunks:
            if chunk.content_type in self.exclude_content_types:
                continue
            if self.include_chunk_levels and chunk.chunk_level not in self.include_chunk_levels:
                continue
            filtered.append(chunk)
        return filtered

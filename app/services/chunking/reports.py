from __future__ import annotations

from collections import Counter
from statistics import mean

from pydantic import BaseModel, Field

from app.schemas.chunk import DocumentChunk


class ChunkQualityReport(BaseModel):
    total_chunks: int
    min_tokens: int = 0
    max_tokens: int = 0
    avg_tokens: float = 0.0
    p50_tokens: int = 0
    p90_tokens: int = 0
    chunks_under_100: int = 0
    chunks_over_900: int = 0
    empty_chunks: int = 0
    duplicate_chunks: int = 0
    suspected_formula_headings: int = 0
    retrieval_excluded_chunks: int = 0
    content_type_distribution: dict[str, int] = Field(default_factory=dict)
    chunk_level_distribution: dict[str, int] = Field(default_factory=dict)
    source_type_distribution: dict[str, int] = Field(default_factory=dict)


class ChunkQualityReporter:
    def build(self, chunks: list[DocumentChunk]) -> ChunkQualityReport:
        if not chunks:
            return ChunkQualityReport(total_chunks=0)

        token_counts = sorted(chunk.token_count for chunk in chunks)
        content_hash_counts = Counter(chunk.content_hash for chunk in chunks)
        content_type_counts = Counter(str(chunk.metadata.content_type) for chunk in chunks)
        chunk_level_counts = Counter(chunk.metadata.chunk_level for chunk in chunks)
        source_type_counts = Counter(str(chunk.metadata.source_type) for chunk in chunks)

        return ChunkQualityReport(
            total_chunks=len(chunks),
            min_tokens=min(token_counts),
            max_tokens=max(token_counts),
            avg_tokens=round(mean(token_counts), 2),
            p50_tokens=self._percentile(token_counts, 50),
            p90_tokens=self._percentile(token_counts, 90),
            chunks_under_100=sum(1 for count in token_counts if count < 100),
            chunks_over_900=sum(1 for count in token_counts if count > 900),
            empty_chunks=sum(1 for chunk in chunks if not chunk.text.strip()),
            duplicate_chunks=sum(count - 1 for count in content_hash_counts.values() if count > 1),
            suspected_formula_headings=sum(
                1
                for chunk in chunks
                if chunk.metadata.section_title and "=" in chunk.metadata.section_title
            ),
            retrieval_excluded_chunks=sum(1 for chunk in chunks if chunk.metadata.retrieval_excluded),
            content_type_distribution=dict(content_type_counts),
            chunk_level_distribution=dict(chunk_level_counts),
            source_type_distribution=dict(source_type_counts),
        )

    def _percentile(self, values: list[int], percentile: int) -> int:
        if not values:
            return 0
        index = round((percentile / 100) * (len(values) - 1))
        return values[index]

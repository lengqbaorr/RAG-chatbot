from __future__ import annotations

from dataclasses import dataclass

from app.services.retrieval.context_selector import ContextSelector
from app.services.retrieval.deduplicator import RetrievalDeduplicator
from app.services.retrieval.filters import ContentTypeFilter, ScoreThresholdFilter
from app.services.retrieval.models import RetrievedChunk


@dataclass
class PostProcessResult:
    chunks: list[RetrievedChunk]
    after_threshold: int
    after_dedup: int


class RetrievalPostProcessor:
    def __init__(
        self,
        *,
        threshold_filter: ScoreThresholdFilter,
        content_type_filter: ContentTypeFilter,
        deduplicator: RetrievalDeduplicator,
        context_selector: ContextSelector,
    ) -> None:
        self.threshold_filter = threshold_filter
        self.content_type_filter = content_type_filter
        self.deduplicator = deduplicator
        self.context_selector = context_selector

    def process(self, chunks: list[RetrievedChunk], *, top_k: int) -> PostProcessResult:
        thresholded = self.threshold_filter.apply(chunks)
        content_filtered = self.content_type_filter.apply(thresholded)
        deduped = self.deduplicator.apply(content_filtered)
        selected = self.context_selector.select(deduped, top_k=top_k)
        return PostProcessResult(
            chunks=selected,
            after_threshold=len(thresholded),
            after_dedup=len(deduped),
        )

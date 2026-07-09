from __future__ import annotations

import logging

from app.services.reranking.config import RerankerConfig
from app.services.reranking.interfaces import BaseReranker
from app.services.reranking.models import RerankedChunk
from app.services.retrieval.models import RetrievedChunk

logger = logging.getLogger(__name__)


class BGERerankerError(Exception):
    pass


class BGERerankerProvider(BaseReranker):
    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()
        self._model = None

    @property
    def provider_name(self) -> str:
        return "bge"

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RerankedChunk]:
        if not chunks:
            return []
        scores = self._predict(query, chunks)
        items = [
            RerankedChunk(
                chunk=chunk,
                original_rank=chunk.rank,
                original_score=chunk.score,
                rerank_score=float(score),
                final_rank=1,
            )
            for chunk, score in zip(chunks, scores, strict=True)
        ]
        items.sort(key=lambda item: item.rerank_score, reverse=True)
        selected = items[:top_k]
        return [
            item.model_copy(update={"final_rank": index})
            for index, item in enumerate(selected, start=1)
        ]

    def _predict(self, query: str, chunks: list[RetrievedChunk]) -> list[float]:
        model = self._get_model()
        pairs = [(query, chunk.content) for chunk in chunks]
        try:
            scores = model.predict(
                pairs,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
            )
        except TypeError:
            scores = model.predict(pairs)
        return [float(score) for score in scores]

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                logger.info("Loading BGE reranker model: %s", self.config.model_name)
                self._model = CrossEncoder(
                    self.config.model_name,
                    device=self.config.device,
                    cache_folder=self.config.cache_folder,
                    max_length=self.config.max_length,
                    local_files_only=self.config.local_files_only,
                )
            except Exception as exc:
                raise BGERerankerError(
                    f"Could not load reranker model '{self.config.model_name}'"
                ) from exc
        return self._model

    def preload(self) -> str:
        self._get_model()
        return self.config.model_name

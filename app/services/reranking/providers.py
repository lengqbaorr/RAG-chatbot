from __future__ import annotations

import logging

from app.services.reranking.interfaces import BaseReranker
from app.services.reranking.models import RerankedChunk, RerankerConfig
from app.services.retrieval.models import RetrievedChunk

logger = logging.getLogger(__name__)


class CrossEncoderReranker(BaseReranker):
    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()
        self._model = None

    def rerank(
        self,
        *,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RerankedChunk]:
        if not chunks:
            return []
        model = self._get_model()
        pairs = [(query, self._rerank_text(chunk)) for chunk in chunks]
        scores = model.predict(pairs)
        reranked = [
            RerankedChunk(
                chunk=chunk,
                rerank_score=float(score),
                original_score=chunk.score,
                original_rank=chunk.rank,
            )
            for chunk, score in zip(chunks, scores, strict=False)
        ]
        reranked.sort(key=lambda item: item.rerank_score, reverse=True)
        return reranked[:top_k]

    def set_model_name(self, model_name: str) -> None:
        if model_name and model_name != self.config.model_name:
            self.config = RerankerConfig(
                model_name=model_name,
                device=self.config.device,
                local_files_only=self.config.local_files_only,
            )
            self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            logger.info("Loading reranker model: %s", self.config.model_name)
            self._model = CrossEncoder(
                self.config.model_name,
                device=self.config.device,
                automodel_args={"local_files_only": self.config.local_files_only},
                tokenizer_args={"local_files_only": self.config.local_files_only},
                config_args={"local_files_only": self.config.local_files_only},
            )
        return self._model

    @staticmethod
    def _rerank_text(chunk: RetrievedChunk) -> str:
        if chunk.retrieved_child is not None:
            return chunk.retrieved_child.content
        return chunk.content

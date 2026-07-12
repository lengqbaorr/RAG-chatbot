from __future__ import annotations

from app.services.reranking.interfaces import BaseReranker
from app.services.retrieval.models import RetrievedContext, RetrievalReport, RetrievalResult


class RerankerService:
    def __init__(self, reranker: BaseReranker, *, rerank_weight: float = 0.35) -> None:
        self.reranker = reranker
        self.rerank_weight = min(max(rerank_weight, 0.0), 1.0)

    def rerank_result(
        self,
        *,
        query: str,
        result: RetrievalResult,
        top_k: int,
        model_name: str | None = None,
    ) -> RetrievalResult:
        if not result.chunks:
            return result

        if model_name and hasattr(self.reranker, "set_model_name"):
            self.reranker.set_model_name(model_name)
        reranked = self.reranker.rerank(query=query, chunks=result.chunks, top_k=len(result.chunks))
        if not reranked:
            return result

        rerank_scores = self._normalize_scores([item.rerank_score for item in reranked])
        fused_items = []
        for item, normalized_rerank_score in zip(reranked, rerank_scores, strict=True):
            original_score = min(max(item.original_score, 0.0), 1.0)
            fused_score = (
                (1.0 - self.rerank_weight) * original_score
                + self.rerank_weight * normalized_rerank_score
            )
            fused_items.append((fused_score, normalized_rerank_score, item))
        fused_items.sort(key=lambda entry: entry[0], reverse=True)

        chunks = []
        for rank, (fused_score, normalized_rerank_score, item) in enumerate(
            fused_items[:top_k],
            start=1,
        ):
            metadata = dict(item.chunk.metadata)
            metadata["original_score"] = item.original_score
            metadata["original_rank"] = item.original_rank
            metadata["rerank_score"] = item.rerank_score
            metadata["rerank_score_normalized"] = round(normalized_rerank_score, 6)
            metadata["fused_score"] = round(fused_score, 6)
            metadata["rerank_weight"] = self.rerank_weight
            chunks.append(
                item.chunk.model_copy(
                    update={
                        "rank": rank,
                        "metadata": metadata,
                        "retrieval_strategy": f"{item.chunk.retrieval_strategy}+rerank",
                    }
                )
            )

        scores = [chunk.score for chunk in chunks]
        report = result.report.model_copy(
            update={
                "top_k": top_k,
                "final_results": len(chunks),
                "min_score": round(min(scores), 4) if scores else 0.0,
                "max_score": round(max(scores), 4) if scores else 0.0,
                "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
                "strategy": f"{result.report.strategy}+rerank",
            }
        )
        context = RetrievedContext(
            query=result.context.query,
            normalized_query=result.context.normalized_query,
            strategy=report.strategy,
            chunks=chunks,
        )
        return RetrievalResult(
            query=result.query,
            normalized_query=result.normalized_query,
            context=context,
            chunks=chunks,
            report=report,
        )

    @staticmethod
    def _normalize_scores(scores: list[float]) -> list[float]:
        if not scores:
            return []
        min_score = min(scores)
        max_score = max(scores)
        if max_score == min_score:
            return [1.0 for _ in scores]
        return [(score - min_score) / (max_score - min_score) for score in scores]

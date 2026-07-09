from __future__ import annotations

from app.services.retrieval.models import RetrievedChunk


class ContextSelector:
    CONTENT_TYPE_PRIORITY = {
        "body": 0,
        "table": 1,
        "code": 2,
        "heading": 3,
        "ocr": 4,
        "reference": 5,
        "toc": 6,
        "cover": 7,
    }

    def select(self, chunks: list[RetrievedChunk], *, top_k: int) -> list[RetrievedChunk]:
        sorted_chunks = sorted(
            chunks,
            key=lambda chunk: (
                -chunk.score,
                self.CONTENT_TYPE_PRIORITY.get(chunk.content_type, 99),
                chunk.rank,
            ),
        )
        selected = sorted_chunks[:top_k]
        return [
            chunk.model_copy(update={"rank": rank})
            for rank, chunk in enumerate(selected, start=1)
        ]

from __future__ import annotations

from app.services.retrieval.models import RetrievedChunk


class RetrievalDeduplicator:
    SUPPORTED_MODES = {"chunk_id", "parent_id", "content_hash", "source_page"}

    def __init__(self, mode: str = "chunk_id") -> None:
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(f"Unsupported deduplication mode: {mode}")
        self.mode = mode

    def apply(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen: set[str] = set()
        deduped: list[RetrievedChunk] = []

        for chunk in chunks:
            key = self._key(chunk)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)

        return deduped

    def _key(self, chunk: RetrievedChunk) -> str:
        if self.mode == "chunk_id":
            return chunk.chunk_id
        if self.mode == "parent_id":
            return chunk.parent_id or chunk.chunk_id
        if self.mode == "content_hash":
            value = chunk.metadata.get("content_hash")
            return str(value or chunk.chunk_id)
        if self.mode == "source_page":
            return "|".join(
                [
                    chunk.source_id,
                    str(chunk.page_start or ""),
                    str(chunk.page_end or ""),
                    chunk.section_title or "",
                ]
            )
        return chunk.chunk_id

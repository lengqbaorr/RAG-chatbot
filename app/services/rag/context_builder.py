from __future__ import annotations

import re

from app.services.chunking.tokenizers import TokenCounter
from app.services.rag.config import ContextBuilderConfig
from app.services.rag.models import BuiltContext, ContextSource
from app.services.retrieval.models import RetrievalResult, RetrievedChunk


class ContextBuilder:
    def __init__(
        self,
        *,
        config: ContextBuilderConfig | None = None,
        token_counter: TokenCounter | None = None,
    ) -> None:
        self.config = config or ContextBuilderConfig()
        self.token_counter = token_counter or TokenCounter()

    def build(self, retrieval_result: RetrievalResult) -> BuiltContext:
        chunks = self._deduplicate(retrieval_result.chunks)
        blocks: list[str] = []
        sources: list[ContextSource] = []
        used_tokens = 0
        truncated = False

        for source_number, chunk in enumerate(chunks, start=1):
            block = self._format_block(source_number, chunk)
            block_tokens = self.token_counter.count(block)
            if used_tokens + block_tokens > self.config.max_context_tokens:
                truncated = True
                if not blocks and self.config.max_context_tokens > 0:
                    truncated_block = self._truncate_to_budget(
                        block,
                        max_tokens=self.config.max_context_tokens,
                    )
                    blocks.append(truncated_block)
                    used_tokens = self.token_counter.count(truncated_block)
                    sources.append(self._source_from_chunk(source_number, chunk))
                break

            blocks.append(block)
            used_tokens += block_tokens
            sources.append(self._source_from_chunk(source_number, chunk))

        return BuiltContext(
            text="\n\n".join(blocks),
            sources=sources,
            token_count=used_tokens,
            truncated=truncated,
        )

    def _deduplicate(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not self.config.deduplicate:
            return chunks

        seen: set[str] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in chunks:
            key = chunk.parent_id or chunk.chunk_id
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)
        return deduped

    def _format_block(self, source_number: int, chunk: RetrievedChunk) -> str:
        lines = [f"[Source {source_number}]"]
        if self.config.include_metadata:
            lines.extend(
                [
                    f"File: {chunk.source_name}",
                    f"Page: {self._format_page(chunk)}",
                    f"Section: {chunk.header_path_text or chunk.section_title or '(none)'}",
                ]
            )
            if self.config.include_scores:
                lines.append(f"Score: {chunk.score:.4f}")
        lines.extend(["Content:", chunk.content.strip()])
        return "\n".join(lines)

    def _source_from_chunk(self, source_number: int, chunk: RetrievedChunk) -> ContextSource:
        preview = chunk.content[:240].replace("\n", " ").strip()
        return ContextSource(
            source_number=source_number,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_id=chunk.source_id,
            source_name=chunk.source_name,
            source_type=chunk.source_type,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            section_title=chunk.header_path_text or chunk.section_title,
            header_path=chunk.header_path,
            score=chunk.score,
            content_preview=preview,
        )

    def _format_page(self, chunk: RetrievedChunk) -> str:
        if chunk.page_start is None and chunk.page_end is None:
            return "(unknown)"
        if chunk.page_start == chunk.page_end or chunk.page_end is None:
            return str(chunk.page_start)
        return f"{chunk.page_start}-{chunk.page_end}"

    def _truncate_to_budget(self, text: str, *, max_tokens: int) -> str:
        parts = re.findall(r"\S+\s*", text, flags=re.UNICODE)
        if not parts:
            return ""

        low = 1
        high = len(parts)
        best = parts[0].strip()
        while low <= high:
            mid = (low + high) // 2
            candidate = "".join(parts[:mid]).strip()
            if self.token_counter.count(candidate) <= max_tokens:
                best = candidate
                low = mid + 1
            else:
                high = mid - 1
        return best

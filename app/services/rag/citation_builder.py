from __future__ import annotations

from app.services.rag.models import BuiltContext, Citation


class CitationBuilder:
    def build(self, context: BuiltContext) -> list[Citation]:
        return [
            Citation(
                source_number=source.source_number,
                source_id=source.source_id,
                source_name=source.source_name,
                page_start=source.page_start,
                page_end=source.page_end,
                section_title=source.section_title,
                chunk_id=source.chunk_id,
                score=source.score,
                content_preview=source.content_preview,
            )
            for source in context.sources
        ]

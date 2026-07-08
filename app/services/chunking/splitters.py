from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, model_validator

from app.schemas.chunk import (
    ChunkMetadata,
    ChunkingStrategy,
    ContentType,
    DocumentChunk,
    StructuredUnit,
    UnitType,
)
from app.schemas.document import Document
from app.services.chunking.hashers import stable_hash
from app.services.chunking.tokenizers import TokenCounter


class ChunkingConfig(BaseModel):
    strategy: ChunkingStrategy = ChunkingStrategy.auto
    chunk_size_tokens: int = Field(default=700, ge=50)
    chunk_overlap_tokens: int = Field(default=100, ge=0)
    min_chunk_tokens: int = Field(default=30, ge=1)
    include_header_context: bool = True
    merge_small_chunks: bool = True
    small_chunk_threshold_tokens: int = Field(default=150, ge=1)
    max_merged_chunk_tokens: int = Field(default=900, ge=50)
    build_parent_chunks: bool = False
    parent_section_first: bool = True
    parent_chunk_size_tokens: int = Field(default=1600, ge=200)
    parent_chunk_overlap_tokens: int = Field(default=120, ge=0)
    parent_chunk_overlap_children: int = Field(default=1, ge=0)
    retrieval_excluded_content_types: set[ContentType] = Field(
        default_factory=lambda: {
            ContentType.cover,
            ContentType.toc,
            ContentType.reference,
        }
    )
    tokenizer_encoding: str = "simple"
    embedding_model: str | None = None
    embedding_version: str | None = None

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")
        if self.min_chunk_tokens > self.chunk_size_tokens:
            raise ValueError("min_chunk_tokens must be smaller than or equal to chunk_size_tokens")
        if self.merge_small_chunks and self.small_chunk_threshold_tokens >= self.max_merged_chunk_tokens:
            raise ValueError("small_chunk_threshold_tokens must be smaller than max_merged_chunk_tokens")
        if self.build_parent_chunks and self.parent_chunk_size_tokens <= self.chunk_size_tokens:
            raise ValueError("parent_chunk_size_tokens should be larger than chunk_size_tokens")
        if self.parent_chunk_overlap_tokens >= self.parent_chunk_size_tokens:
            raise ValueError("parent_chunk_overlap_tokens must be smaller than parent_chunk_size_tokens")
        return self


class BaseSplitter(ABC):
    def __init__(self, config: ChunkingConfig, token_counter: TokenCounter | None = None) -> None:
        self.config = config
        self.token_counter = token_counter or TokenCounter(config.tokenizer_encoding)

    @abstractmethod
    def split(self, document: Document, units: list[StructuredUnit]) -> list[DocumentChunk]:
        raise NotImplementedError


class RecursiveTokenSplitter(BaseSplitter):
    strategy = ChunkingStrategy.recursive_token

    def split(self, document: Document, units: list[StructuredUnit]) -> list[DocumentChunk]:
        normalized_units = self._expand_oversized_units(units)
        grouped_units = self._group_units(normalized_units, force_new_on_heading=False)
        return self._to_chunks(document, grouped_units)

    def _group_units(
        self,
        units: list[StructuredUnit],
        *,
        force_new_on_heading: bool,
    ) -> list[list[StructuredUnit]]:
        groups: list[list[StructuredUnit]] = []
        current: list[StructuredUnit] = []
        current_tokens = 0

        for unit in units:
            starts_new_section = force_new_on_heading and unit.unit_type == UnitType.heading
            would_exceed = current and current_tokens + unit.token_count > self.config.chunk_size_tokens
            current_has_min_size = current_tokens >= self.config.min_chunk_tokens

            if current and (would_exceed or (starts_new_section and current_has_min_size)):
                groups.append(current)
                current = self._overlap_tail(current)
                current_tokens = sum(item.token_count for item in current)

            current.append(unit)
            current_tokens += unit.token_count

        if current:
            groups.append(current)

        return groups

    def _overlap_tail(self, units: list[StructuredUnit]) -> list[StructuredUnit]:
        if self.config.chunk_overlap_tokens == 0:
            return []

        overlap: list[StructuredUnit] = []
        tokens = 0
        for unit in reversed(units):
            if unit.token_count > self.config.chunk_overlap_tokens and not overlap:
                break
            if tokens + unit.token_count > self.config.chunk_overlap_tokens and overlap:
                break
            overlap.insert(0, unit)
            tokens += unit.token_count
            if tokens >= self.config.chunk_overlap_tokens:
                break

        return overlap

    def _expand_oversized_units(self, units: list[StructuredUnit]) -> list[StructuredUnit]:
        expanded: list[StructuredUnit] = []
        for unit in units:
            if unit.token_count <= self.config.chunk_size_tokens:
                expanded.append(unit)
                continue

            parts = self.token_counter.split_by_tokens(
                unit.text,
                chunk_size=self.config.chunk_size_tokens,
                chunk_overlap=self.config.chunk_overlap_tokens,
            )
            for part_index, part in enumerate(parts):
                expanded.append(
                    unit.model_copy(
                        update={
                            "unit_id": stable_hash(unit.unit_id, "part", part_index, part[:512]),
                            "text": part,
                            "token_count": self.token_counter.count(part),
                        }
                    )
                )

        return expanded

    def _to_chunks(self, document: Document, groups: list[list[StructuredUnit]]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for chunk_index, group in enumerate(groups):
            text = self._chunk_text(group)
            token_count = self.token_counter.count(text)
            content_hash = stable_hash(text)
            chunk_id = stable_hash(document.metadata.document_id, chunk_index, content_hash, self.strategy)
            page_numbers = [page for unit in group for page in (unit.page_start, unit.page_end) if page is not None]
            char_starts = [unit.char_start for unit in group if unit.char_start is not None]
            char_ends = [unit.char_end for unit in group if unit.char_end is not None]
            header_path = self._dominant_header_path(group)
            content_type = self._dominant_content_type(group)

            metadata = ChunkMetadata(
                source_id=group[0].source_id,
                source_name=document.metadata.title or document.metadata.source,
                source_type=document.metadata.document_type,
                page_start=min(page_numbers) if page_numbers else None,
                page_end=max(page_numbers) if page_numbers else None,
                section_title=header_path[-1] if header_path else None,
                header_path=header_path,
                chunk_index=chunk_index,
                token_count=token_count,
                content_hash=content_hash,
                parent_id=document.metadata.document_id,
                char_start=min(char_starts) if char_starts else None,
                char_end=max(char_ends) if char_ends else None,
                content_type=content_type,
                retrieval_excluded=self._is_retrieval_excluded(content_type),
                language=self._detect_language(text),
                chunk_level="child",
                embedding_text_hash=content_hash,
                parser_version="structure_parser_v1",
                chunker_version=f"{self.strategy}_v1",
                chunk_strategy=self.strategy,
                embedding_model=self.config.embedding_model,
                embedding_version=self.config.embedding_version,
            )

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document.metadata.document_id,
                    source_id=group[0].source_id,
                    text=text,
                    chunk_index=chunk_index,
                    token_count=token_count,
                    content_hash=content_hash,
                    metadata=metadata,
                )
            )

        return chunks

    def _chunk_text(self, group: list[StructuredUnit]) -> str:
        body = "\n".join(unit.text for unit in group if unit.text.strip()).strip()
        if not self.config.include_header_context:
            return body

        header_path = self._dominant_header_path(group)
        if not header_path:
            return body

        context = " > ".join(header_path)
        first_lines = body.split("\n", maxsplit=8)
        if body.startswith(context) or header_path[-1] in first_lines:
            return body
        return f"Section: {context}\n\n{body}"

    def _dominant_header_path(self, group: list[StructuredUnit]) -> list[str]:
        for unit in reversed(group):
            if unit.header_path:
                return list(unit.header_path)
        return []

    def _dominant_content_type(self, group: list[StructuredUnit]) -> ContentType:
        priority = [
            ContentType.toc,
            ContentType.reference,
            ContentType.cover,
            ContentType.table,
            ContentType.code,
            ContentType.ocr,
            ContentType.body,
            ContentType.heading,
        ]
        content_types = {unit.content_type for unit in group}
        for content_type in priority:
            if content_type in content_types:
                return content_type
        return ContentType.body

    def _is_retrieval_excluded(self, content_type: ContentType) -> bool:
        return content_type in self.config.retrieval_excluded_content_types

    def _detect_language(self, text: str) -> str:
        vietnamese_chars = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
        lowered = text.casefold()
        return "vi" if any(char in lowered for char in vietnamese_chars) else "unknown"


class MarkdownHeadingSplitter(RecursiveTokenSplitter):
    strategy = ChunkingStrategy.markdown_heading

    def split(self, document: Document, units: list[StructuredUnit]) -> list[DocumentChunk]:
        normalized_units = self._expand_oversized_units(units)
        grouped_units = self._group_units(normalized_units, force_new_on_heading=True)
        return self._to_chunks(document, grouped_units)

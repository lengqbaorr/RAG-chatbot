from __future__ import annotations

import re
from collections.abc import Iterable

from app.schemas.chunk import ContentType, DocumentChunk
from app.services.chunking.hashers import stable_hash
from app.services.chunking.splitters import ChunkingConfig
from app.services.chunking.tokenizers import TokenCounter


class SmallChunkMerger:
    def __init__(self, config: ChunkingConfig, token_counter: TokenCounter) -> None:
        self.config = config
        self.token_counter = token_counter

    def merge(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if not self.config.merge_small_chunks or len(chunks) < 2:
            return chunks

        merged: list[DocumentChunk] = []
        index = 0
        while index < len(chunks):
            current = chunks[index]
            if (
                current.token_count < self.config.small_chunk_threshold_tokens
                and index + 1 < len(chunks)
                and self._can_merge(current, chunks[index + 1])
            ):
                merged.append(self._merge_pair(current, chunks[index + 1]))
                index += 2
                continue

            merged.append(current)
            index += 1

        return self._renumber(merged)

    def _can_merge(self, left: DocumentChunk, right: DocumentChunk) -> bool:
        if left.source_id != right.source_id:
            return False
        if left.document_id != right.document_id:
            return False
        if not self._compatible_content_type(left.metadata.content_type, right.metadata.content_type):
            return False
        if left.metadata.header_path and right.metadata.header_path:
            if left.metadata.header_path != right.metadata.header_path:
                return False
        if not self._pages_are_close(left, right):
            return False
        return left.token_count + right.token_count <= self.config.max_merged_chunk_tokens

    def _compatible_content_type(self, left: ContentType, right: ContentType) -> bool:
        if left == right:
            return True
        compatible = {ContentType.body, ContentType.heading}
        return left in compatible and right in compatible

    def _pages_are_close(self, left: DocumentChunk, right: DocumentChunk) -> bool:
        left_end = left.metadata.page_end
        right_start = right.metadata.page_start
        if left_end is None or right_start is None:
            return True
        return right_start - left_end <= 1

    def _merge_pair(self, left: DocumentChunk, right: DocumentChunk) -> DocumentChunk:
        text = f"{left.text.rstrip()}\n\n{right.text.lstrip()}".strip()
        token_count = self.token_counter.count(text)
        content_hash = stable_hash(text)
        metadata = left.metadata.model_copy(
            update={
                "page_start": self._min_present([left.metadata.page_start, right.metadata.page_start]),
                "page_end": self._max_present([left.metadata.page_end, right.metadata.page_end]),
                "token_count": token_count,
                "content_hash": content_hash,
                "embedding_text_hash": content_hash,
                "char_start": self._min_present([left.metadata.char_start, right.metadata.char_start]),
                "char_end": self._max_present([left.metadata.char_end, right.metadata.char_end]),
                "child_ids": [left.chunk_id, right.chunk_id],
                "content_type": self._merged_content_type(left.metadata.content_type, right.metadata.content_type),
                "retrieval_excluded": self._is_retrieval_excluded(left, right),
            }
        )

        chunk_id = stable_hash(left.document_id, "merged", left.chunk_id, right.chunk_id, content_hash)
        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=left.document_id,
            source_id=left.source_id,
            text=text,
            chunk_index=left.chunk_index,
            token_count=token_count,
            content_hash=content_hash,
            metadata=metadata,
        )

    def _renumber(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        renumbered: list[DocumentChunk] = []
        for index, chunk in enumerate(chunks):
            metadata = chunk.metadata.model_copy(update={"chunk_index": index})
            renumbered.append(chunk.model_copy(update={"chunk_index": index, "metadata": metadata}))
        return renumbered

    def _merged_content_type(self, left: ContentType, right: ContentType) -> ContentType:
        if left == right:
            return left
        return ContentType.body

    def _is_retrieval_excluded(self, left: DocumentChunk, right: DocumentChunk) -> bool:
        if self._merged_content_type(left.metadata.content_type, right.metadata.content_type) == ContentType.body:
            return False
        return left.metadata.retrieval_excluded and right.metadata.retrieval_excluded

    def _min_present(self, values: Iterable[int | None]) -> int | None:
        present = [value for value in values if value is not None]
        return min(present) if present else None

    def _max_present(self, values: Iterable[int | None]) -> int | None:
        present = [value for value in values if value is not None]
        return max(present) if present else None


class ParentChunkBuilder:
    def __init__(self, config: ChunkingConfig, token_counter: TokenCounter) -> None:
        self.config = config
        self.token_counter = token_counter

    def build(self, child_chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if not child_chunks:
            return []

        sorted_children = sorted(
            child_chunks,
            key=lambda chunk: (
                chunk.source_id,
                chunk.metadata.page_start or 0,
                chunk.metadata.chunk_index,
                chunk.chunk_id,
            ),
        )

        parents: list[DocumentChunk] = []
        current: list[DocumentChunk] = []
        current_tokens = 0
        overlap_prefix: str | None = None
        overlap_tokens = 0

        for child in sorted_children:
            if child.metadata.chunk_level != "child":
                continue

            child_section = self._section_key(child)
            current_section = self._section_key(current[-1]) if current else None
            would_exceed = (
                current
                and current_tokens + child.token_count > self.config.parent_chunk_size_tokens
            )
            source_changed = current and current[-1].source_id != child.source_id
            section_changed = (
                current
                and self.config.parent_section_first
                and current_section != child_section
            )
            section_boundary = bool(section_changed)

            if current and (would_exceed or source_changed or section_boundary):
                parent = self._to_parent_chunk(current, len(parents), overlap_prefix)
                if parent is not None:
                    parents.append(parent)

                should_overlap = bool(would_exceed and not source_changed and not section_boundary)
                parent_text = parent.text if parent is not None else self._group_text(current)
                overlap_prefix = self._overlap_text(parent_text) if should_overlap else None
                overlap_tokens = self.token_counter.count(overlap_prefix or "")
                current = []
                current_tokens = overlap_tokens

            current.append(child)
            current_tokens += child.token_count

        if current:
            parent = self._to_parent_chunk(current, len(parents), overlap_prefix)
            if parent is not None:
                parents.append(parent)

        return parents

    def attach_parent_ids(
        self,
        child_chunks: list[DocumentChunk],
        parent_chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        child_to_parent: dict[str, str] = {}
        for parent in parent_chunks:
            for child_id in parent.metadata.child_ids:
                child_to_parent.setdefault(child_id, parent.chunk_id)

        attached: list[DocumentChunk] = []
        for child in child_chunks:
            parent_id = child_to_parent.get(child.chunk_id, child.metadata.parent_id)
            metadata = child.metadata.model_copy(update={"parent_id": parent_id})
            attached.append(child.model_copy(update={"metadata": metadata}))
        return attached

    def _to_parent_chunk(
        self,
        children: list[DocumentChunk],
        parent_index: int,
        overlap_prefix: str | None = None,
    ) -> DocumentChunk | None:
        if len(children) == 1 and not overlap_prefix:
            return None

        text_parts = [child.text for child in children if child.text.strip()]
        if overlap_prefix:
            text_parts.insert(0, f"Context overlap:\n{overlap_prefix.strip()}")
        text = "\n\n".join(text_parts).strip()
        token_count = self.token_counter.count(text)
        content_hash = stable_hash(text)
        first = children[0]
        header_path = self._parent_header_path(children)
        content_type = self._dominant_content_type(children)
        page_start = self._min_present(child.metadata.page_start for child in children)
        page_end = self._max_present(child.metadata.page_end for child in children)
        source_name = first.metadata.source_name
        chunk_id = stable_hash(first.source_id, "parent", parent_index, content_hash)

        metadata = first.metadata.model_copy(
            update={
                "source_name": source_name,
                "page_start": page_start,
                "page_end": page_end,
                "section_title": header_path[-1] if header_path else None,
                "header_path": header_path,
                "chunk_index": parent_index,
                "token_count": token_count,
                "content_hash": content_hash,
                "parent_id": None,
                "child_ids": [child.chunk_id for child in children],
                "content_type": content_type,
                "retrieval_excluded": self._is_parent_retrieval_excluded(children, content_type),
                "language": self._dominant_language(children),
                "chunk_level": "parent",
                "embedding_text_hash": content_hash,
                "chunker_version": "parent_child_v1",
                "char_start": self._min_present(child.metadata.char_start for child in children),
                "char_end": self._max_present(child.metadata.char_end for child in children),
            }
        )

        return DocumentChunk(
            chunk_id=chunk_id,
            document_id=first.source_id,
            source_id=first.source_id,
            text=text,
            chunk_index=parent_index,
            token_count=token_count,
            content_hash=content_hash,
            metadata=metadata,
        )

    def _section_key(self, child: DocumentChunk) -> tuple[str, ...]:
        special_types = {ContentType.cover, ContentType.toc, ContentType.reference}
        if child.metadata.content_type in special_types:
            return (child.source_id, "content_type", str(child.metadata.content_type))
        section_label = self._parent_section_label(child.metadata.header_path)
        if section_label:
            return (child.source_id, "section", section_label)
        return (child.source_id, "section", "__default__")

    def _parent_section_label(self, header_path: list[str]) -> str | None:
        if not header_path:
            return None

        for title in header_path:
            number = self._heading_number(title)
            if not number:
                continue
            parts = number.split(".")
            return ".".join(parts[:2]) if len(parts) >= 2 else parts[0]

        return header_path[0]

    def _group_text(self, children: list[DocumentChunk]) -> str:
        return "\n\n".join(child.text for child in children if child.text.strip()).strip()

    def _overlap_text(self, text: str) -> str | None:
        if self.config.parent_chunk_overlap_tokens == 0:
            return None

        parts = self.token_counter.split_by_tokens(
            text,
            chunk_size=self.config.parent_chunk_overlap_tokens,
            chunk_overlap=0,
        )
        if not parts:
            return None
        tail = parts[-1].strip()
        return tail or None

    def _parent_header_path(self, children: list[DocumentChunk]) -> list[str]:
        paths = [child.metadata.header_path for child in children if child.metadata.header_path]
        if not paths:
            return []

        common_prefix = self._common_header_prefix(paths)
        if common_prefix:
            return common_prefix[:-1] if len(common_prefix) > 1 else common_prefix

        first_path = list(paths[0])
        numeric_parent = self._common_numeric_parent(paths)
        if numeric_parent:
            first_number = self._heading_number(first_path[0])
            if first_number == numeric_parent:
                return [first_path[0]]
            return [numeric_parent]

        parent_number = self._heading_number(first_path[0])
        if parent_number:
            for path in paths[1:]:
                child_number = self._heading_number(path[0])
                if child_number and child_number.startswith(f"{parent_number}."):
                    return [first_path[0]]

        return [first_path[0]]

    def _common_header_prefix(self, paths: list[list[str]]) -> list[str]:
        prefix: list[str] = []
        for values in zip(*paths, strict=False):
            first = values[0]
            if all(value == first for value in values):
                prefix.append(first)
                continue
            break
        return prefix

    def _heading_number(self, title: str) -> str | None:
        match = re.match(r"^\s*(\d+(?:\.\d+)*)", title)
        if match:
            return match.group(1)
        return None

    def _common_numeric_parent(self, paths: list[list[str]]) -> str | None:
        numbers = [self._heading_number(path[0]) for path in paths if path]
        numbers = [number for number in numbers if number]
        if len(numbers) < 2:
            return None

        split_numbers = [number.split(".") for number in numbers]
        common: list[str] = []
        for values in zip(*split_numbers, strict=False):
            first = values[0]
            if all(value == first for value in values):
                common.append(first)
                continue
            break
        if len(common) < 2:
            return None
        return ".".join(common)

    def _dominant_content_type(self, children: list[DocumentChunk]) -> ContentType:
        content_types = {child.metadata.content_type for child in children}
        if ContentType.body in content_types:
            return ContentType.body

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
        for content_type in priority:
            if content_type in content_types:
                return content_type
        return ContentType.body

    def _is_parent_retrieval_excluded(
        self,
        children: list[DocumentChunk],
        content_type: ContentType,
    ) -> bool:
        if content_type not in self.config.retrieval_excluded_content_types:
            return False
        return all(child.metadata.retrieval_excluded for child in children)

    def _dominant_language(self, children: list[DocumentChunk]) -> str | None:
        languages = [child.metadata.language for child in children if child.metadata.language]
        if not languages:
            return None
        return max(set(languages), key=languages.count)

    def _min_present(self, values: Iterable[int | None]) -> int | None:
        present = [value for value in values if value is not None]
        return min(present) if present else None

    def _max_present(self, values: Iterable[int | None]) -> int | None:
        present = [value for value in values if value is not None]
        return max(present) if present else None

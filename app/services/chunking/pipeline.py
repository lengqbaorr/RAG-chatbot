from __future__ import annotations

from app.schemas.chunk import ChunkingStrategy, DocumentChunk
from app.schemas.document import Document, DocumentType
from app.services.chunking.normalizers import TextNormalizer
from app.services.chunking.parsers import StructureParser
from app.services.chunking.postprocessors import ParentChunkBuilder, SmallChunkMerger
from app.services.chunking.splitters import ChunkingConfig, MarkdownHeadingSplitter, RecursiveTokenSplitter
from app.services.chunking.tokenizers import TokenCounter
from app.services.chunking.validators import ChunkValidator


class DocumentChunker:
    def __init__(
        self,
        config: ChunkingConfig | None = None,
        normalizer: TextNormalizer | None = None,
        parser: StructureParser | None = None,
    ) -> None:
        self.config = config or ChunkingConfig()
        self.token_counter = TokenCounter(self.config.tokenizer_encoding)
        self.normalizer = normalizer or TextNormalizer()
        self.parser = parser or StructureParser(self.token_counter)
        max_tokens = (
            self.config.max_merged_chunk_tokens
            if self.config.merge_small_chunks
            else self.config.chunk_size_tokens
        )
        self.merger = SmallChunkMerger(self.config, self.token_counter)
        self.parent_builder = ParentChunkBuilder(self.config, self.token_counter)
        self.validator = ChunkValidator(max_tokens=max_tokens)

    def chunk_documents(self, documents: list[Document]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for document in documents:
            chunks.extend(self.chunk_document(document))
        if self.config.build_parent_chunks:
            parent_chunks = self.parent_builder.build(chunks)
            chunks = self.parent_builder.attach_parent_ids(chunks, parent_chunks)
            chunks.extend(parent_chunks)
        return chunks

    def build_parent_chunks(self, child_chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        return self.parent_builder.build(child_chunks)

    def chunk_document(self, document: Document) -> list[DocumentChunk]:
        normalized_document = document.model_copy(
            update={"text": self.normalizer.normalize(document.text)}
        )
        if not normalized_document.text:
            return []

        units = self.parser.parse(normalized_document)
        if not units:
            return []

        splitter = self._select_splitter(normalized_document)
        chunks = splitter.split(normalized_document, units)
        chunks = self.merger.merge(chunks)
        self.validator.validate(chunks)
        return chunks

    def _select_splitter(self, document: Document):
        strategy = self.config.strategy
        if strategy == ChunkingStrategy.auto:
            strategy = (
                ChunkingStrategy.markdown_heading
                if document.metadata.document_type == DocumentType.markdown
                else ChunkingStrategy.recursive_token
            )

        if strategy == ChunkingStrategy.markdown_heading:
            return MarkdownHeadingSplitter(self.config, self.token_counter)
        if strategy == ChunkingStrategy.recursive_token:
            return RecursiveTokenSplitter(self.config, self.token_counter)

        raise NotImplementedError(f"Chunking strategy is not implemented yet: {strategy}")

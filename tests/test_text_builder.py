from app.schemas.chunk import ChunkMetadata, ChunkingStrategy, ContentType, DocumentChunk
from app.schemas.document import DocumentType
from app.services.embedding.text_builder import EmbeddingTextBuilder


def _make_chunk(
    source_name: str = "test.pdf",
    header_path: list[str] | None = None,
    section_title: str | None = None,
    text: str = "Hello world",
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id="chunk_001",
        document_id="doc_001",
        source_id="src_001",
        text=text,
        chunk_index=0,
        token_count=10,
        content_hash="abc123",
        metadata=ChunkMetadata(
            source_id="src_001",
            source_name=source_name,
            source_type=DocumentType.pdf,
            chunk_index=0,
            token_count=10,
            content_hash="abc123",
            header_path=header_path or [],
            section_title=section_title,
            content_type=ContentType.body,
            retrieval_excluded=False,
            embedding_text_hash="",
            chunk_strategy=ChunkingStrategy.recursive_token,
        ),
    )


class TestEmbeddingTextBuilder:
    def test_build_with_header_path(self):
        chunk = _make_chunk(
            source_name="report.pdf",
            header_path=["Introduction", "Background"],
        )
        builder = EmbeddingTextBuilder()
        result = builder.build(chunk)

        assert "Document: report.pdf" in result
        assert "Section: Introduction > Background" in result
        assert "Content:" in result
        assert "Hello world" in result

    def test_build_with_section_title_fallback(self):
        chunk = _make_chunk(
            source_name="doc.txt",
            section_title="Methodology",
        )
        builder = EmbeddingTextBuilder()
        result = builder.build(chunk)

        assert "Document: doc.txt" in result
        assert "Section: Methodology" in result
        assert "Content:" in result

    def test_build_without_section(self):
        chunk = _make_chunk(source_name="notes.txt")
        builder = EmbeddingTextBuilder()
        result = builder.build(chunk)

        assert "Document: notes.txt" in result
        assert "Content:" in result
        assert "Section:" not in result

    def test_build_does_not_leak_technical_fields(self):
        chunk = _make_chunk()
        builder = EmbeddingTextBuilder()
        result = builder.build(chunk)

        assert chunk.chunk_id not in result
        assert chunk.content_hash not in result

    def test_build_unknown_source_name(self):
        chunk = _make_chunk(source_name="")
        builder = EmbeddingTextBuilder()
        result = builder.build(chunk)

        assert "Document: unknown" in result

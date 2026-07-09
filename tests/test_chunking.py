from pathlib import Path

import pytest

from app.schemas.chunk import ChunkingStrategy, ContentType, UnitType
from app.schemas.document import Document, DocumentMetadata, DocumentType
from app.services.chunking import (
    ChunkQualityReporter,
    ChunkingConfig,
    DocumentChunker,
    StructureParser,
    TextNormalizer,
)
from app.services.ingestion import DocumentLoaderService, LoaderInput


def _document(text: str, document_type: DocumentType = DocumentType.txt) -> Document:
    return Document(
        text=text,
        metadata=DocumentMetadata(
            document_id="doc-1",
            document_type=document_type,
            source="memory://doc-1",
            title="Doc 1",
            page_number=1,
        ),
    )


def test_normalizer_cleans_whitespace_and_broken_words() -> None:
    text = "Alpha-\n beta\n\n\nGamma\t Delta\u200b"

    assert TextNormalizer().normalize(text) == "Alpha-\nbeta\nGamma Delta"


def test_structure_parser_detects_markdown_headings_and_tables() -> None:
    document = _document(
        "# Title\nIntro\n## Table\n| A | B |\n| 1 | 2 |\n```python\nprint('x')\n```",
        DocumentType.markdown,
    )

    units = StructureParser().parse(document)

    assert [unit.unit_type for unit in units] == [
        UnitType.heading,
        UnitType.paragraph,
        UnitType.heading,
        UnitType.table,
        UnitType.code,
    ]
    assert units[1].header_path == ["Title"]
    assert units[3].header_path == ["Title", "Table"]


def test_pdf_formula_is_not_detected_as_heading() -> None:
    document = _document("5 A = 2s2√3\nActual paragraph", DocumentType.pdf)

    units = StructureParser().parse(document)

    assert all(unit.unit_type != UnitType.heading for unit in units)
    assert all("5 A = 2s2√3" not in unit.header_path for unit in units)


def test_short_document_produces_one_metadata_rich_chunk() -> None:
    chunks = DocumentChunker().chunk_document(_document("Short text about RAG chunking."))

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.text == "Short text about RAG chunking."
    assert chunk.metadata.source_name == "Doc 1"
    assert chunk.metadata.page_start == 1
    assert chunk.metadata.page_end == 1
    assert chunk.metadata.parent_id == "doc-1"
    assert chunk.metadata.content_type == ContentType.body
    assert chunk.metadata.retrieval_excluded is False
    assert chunk.metadata.chunk_level == "child"
    assert chunk.metadata.embedding_text_hash == chunk.content_hash
    assert chunk.content_hash == chunk.metadata.content_hash


def test_long_document_is_split_by_token_budget() -> None:
    text = "\n".join(f"Sentence {index} talks about retrieval augmented generation." for index in range(120))
    config = ChunkingConfig(
        chunk_size_tokens=80,
        chunk_overlap_tokens=15,
        min_chunk_tokens=20,
        merge_small_chunks=False,
    )

    chunks = DocumentChunker(config=config).chunk_document(_document(text))

    assert len(chunks) > 1
    assert all(chunk.token_count <= 112 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunk_ids_are_deterministic() -> None:
    document = _document("One\nTwo\nThree\nFour\nFive")
    config = ChunkingConfig(chunk_size_tokens=50, chunk_overlap_tokens=5)

    first = DocumentChunker(config=config).chunk_document(document)
    second = DocumentChunker(config=config).chunk_document(document)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_invalid_config_rejects_overlap_larger_than_chunk_size() -> None:
    with pytest.raises(ValueError):
        ChunkingConfig(chunk_size_tokens=100, chunk_overlap_tokens=100)


def test_markdown_strategy_starts_new_chunks_on_headings() -> None:
    document = _document(
        "# A\n"
        + "\n".join(f"A line {index}" for index in range(12))
        + "\n# B\n"
        + "\n".join(f"B line {index}" for index in range(12)),
        DocumentType.markdown,
    )
    config = ChunkingConfig(
        strategy=ChunkingStrategy.markdown_heading,
        chunk_size_tokens=80,
        chunk_overlap_tokens=0,
        min_chunk_tokens=10,
    )

    chunks = DocumentChunker(config=config).chunk_document(document)

    assert len(chunks) >= 2
    assert any(chunk.metadata.header_path == ["B"] for chunk in chunks)


def test_section_context_uses_explicit_label() -> None:
    document = _document("## Context\nDetailed body text", DocumentType.markdown)
    chunks = DocumentChunker(
        config=ChunkingConfig(
            strategy=ChunkingStrategy.markdown_heading,
            include_header_context=True,
        )
    ).chunk_document(document)

    assert chunks[0].text.startswith("## Context") or "Section: Context" in chunks[0].text


def test_small_chunks_are_merged_when_compatible() -> None:
    document = _document(
        "\n".join(
            [
                "2.1. Section",
                "Short intro.",
                " ".join(f"continuation-{index}" for index in range(45)),
            ]
        )
    )
    config = ChunkingConfig(
        chunk_size_tokens=50,
        chunk_overlap_tokens=0,
        min_chunk_tokens=5,
        small_chunk_threshold_tokens=20,
        max_merged_chunk_tokens=150,
    )

    chunks = DocumentChunker(config=config).chunk_document(document)

    assert len(chunks) <= 2
    assert any(chunk.metadata.child_ids for chunk in chunks)


def test_quality_report_counts_distribution() -> None:
    chunks = DocumentChunker().chunk_document(_document("Short text about RAG chunking."))

    report = ChunkQualityReporter().build(chunks)

    assert report.total_chunks == 1
    assert report.chunks_under_100 == 1
    assert report.empty_chunks == 0
    assert report.content_type_distribution[str(ContentType.body)] == 1
    assert report.chunk_level_distribution["child"] == 1


def test_pdf_first_page_is_marked_as_cover() -> None:
    chunks = DocumentChunker().chunk_document(
        _document("UNIVERSITY\nREPORT TITLE\nStudent name", DocumentType.pdf)
    )

    assert chunks[0].metadata.content_type == ContentType.cover
    assert chunks[0].metadata.retrieval_excluded is True


def test_toc_and_reference_are_excluded_from_default_retrieval() -> None:
    toc_chunks = DocumentChunker().chunk_document(_document("Mục lục\n1. Giới thiệu", DocumentType.pdf))
    reference_chunks = DocumentChunker().chunk_document(
        _document("Tài liệu tham khảo\n[1] Example", DocumentType.pdf)
    )

    assert toc_chunks[0].metadata.content_type == ContentType.toc
    assert toc_chunks[0].metadata.retrieval_excluded is True
    assert reference_chunks[0].metadata.content_type == ContentType.reference
    assert reference_chunks[0].metadata.retrieval_excluded is True


def test_parent_chunks_are_built_from_children() -> None:
    text = "\n".join(
        f"Paragraph {index} explains retrieval augmented generation with enough context."
        for index in range(80)
    )
    config = ChunkingConfig(
        chunk_size_tokens=120,
        chunk_overlap_tokens=0,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_chunk_size_tokens=500,
    )

    chunks = DocumentChunker(config=config).chunk_document(_document(text))
    parent_chunks = DocumentChunker(config=config).build_parent_chunks(chunks)
    attached_children = DocumentChunker(config=config).parent_builder.attach_parent_ids(
        chunks,
        parent_chunks,
    )

    assert len(parent_chunks) >= 1
    assert all(parent.metadata.chunk_level == "parent" for parent in parent_chunks)
    assert all(parent.metadata.child_ids for parent in parent_chunks)
    assert any(child.metadata.parent_id in {parent.chunk_id for parent in parent_chunks} for child in attached_children)


def test_parent_builder_prefers_section_boundaries() -> None:
    document = _document(
        "# Section A\n"
        + "\n".join(f"alpha detail {index} explains section boundaries" for index in range(80))
        + "\n# Section B\n"
        + "\n".join(f"beta detail {index} explains section boundaries" for index in range(80)),
        DocumentType.markdown,
    )
    config = ChunkingConfig(
        strategy=ChunkingStrategy.markdown_heading,
        chunk_size_tokens=70,
        chunk_overlap_tokens=0,
        min_chunk_tokens=10,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_chunk_size_tokens=500,
    )

    chunks = DocumentChunker(config=config).chunk_documents([document])
    parent_chunks = [chunk for chunk in chunks if chunk.metadata.chunk_level == "parent"]

    assert len(parent_chunks) >= 2
    assert all(
        not ("Section A" in parent.text and "Section B" in parent.text)
        for parent in parent_chunks
    )


def test_parent_builder_skips_single_child_parent_duplicates() -> None:
    chunks = DocumentChunker(
        config=ChunkingConfig(build_parent_chunks=True)
    ).chunk_documents([_document("Only one short child chunk.")])

    assert [chunk.metadata.chunk_level for chunk in chunks] == ["child"]
    assert ChunkQualityReporter().build(chunks).duplicate_chunks == 0


def test_parent_builder_does_not_merge_small_tail_into_next_section() -> None:
    document = _document(
        "# Section A\n"
        + "\n".join(f"alpha detail {index} explains tail isolation" for index in range(72))
        + "\nalpha tail marker must stay outside section b parent"
        + "\n# Section B\n"
        + "\n".join(f"beta detail {index} explains next section" for index in range(80)),
        DocumentType.markdown,
    )
    config = ChunkingConfig(
        strategy=ChunkingStrategy.markdown_heading,
        chunk_size_tokens=70,
        chunk_overlap_tokens=0,
        min_chunk_tokens=10,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_chunk_size_tokens=500,
    )

    chunks = DocumentChunker(config=config).chunk_documents([document])
    parent_chunks = [chunk for chunk in chunks if chunk.metadata.chunk_level == "parent"]

    assert parent_chunks
    assert all(
        not ("alpha tail marker" in parent.text and "Section B" in parent.text)
        for parent in parent_chunks
    )


def test_parent_metadata_trims_leaf_subsection_for_parent_chunks() -> None:
    document = _document(
        "# Section A\n"
        "## A.1\n"
        + "\n".join(f"alpha detail {index} explains parent section metadata" for index in range(90)),
        DocumentType.markdown,
    )
    config = ChunkingConfig(
        strategy=ChunkingStrategy.markdown_heading,
        chunk_size_tokens=70,
        chunk_overlap_tokens=0,
        min_chunk_tokens=10,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_chunk_size_tokens=500,
    )

    chunks = DocumentChunker(config=config).chunk_documents([document])
    parent_chunks = [chunk for chunk in chunks if chunk.metadata.chunk_level == "parent"]

    assert parent_chunks
    assert parent_chunks[0].metadata.header_path == ["Section A"]
    assert parent_chunks[0].metadata.section_title == "Section A"


def test_parent_overlap_adds_context_when_splitting_same_section() -> None:
    text = "\n".join(f"shared section detail {index}" for index in range(120))
    config = ChunkingConfig(
        chunk_size_tokens=60,
        chunk_overlap_tokens=0,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_section_first=True,
        parent_chunk_size_tokens=220,
        parent_chunk_overlap_tokens=30,
    )

    chunks = DocumentChunker(config=config).chunk_documents([_document(text)])
    parent_chunks = [chunk for chunk in chunks if chunk.metadata.chunk_level == "parent"]

    assert len(parent_chunks) >= 2
    assert any(parent.text.startswith("Context overlap:") for parent in parent_chunks[1:])


def test_chunk_documents_can_include_parent_chunks() -> None:
    text = "\n".join(
        f"Paragraph {index} explains retrieval augmented generation with enough context."
        for index in range(80)
    )
    config = ChunkingConfig(
        chunk_size_tokens=120,
        chunk_overlap_tokens=0,
        merge_small_chunks=False,
        build_parent_chunks=True,
        parent_chunk_size_tokens=500,
    )

    chunks = DocumentChunker(config=config).chunk_documents([_document(text)])
    report = ChunkQualityReporter().build(chunks)

    assert report.chunk_level_distribution["child"] >= 1
    assert report.chunk_level_distribution["parent"] >= 1
    assert report.retrieval_excluded_chunks >= 0


def test_real_pdf_file_can_be_chunked() -> None:
    source = Path("Test.pdf")
    if not source.exists():
        pytest.skip("real PDF sample is not available")

    documents = DocumentLoaderService().load(LoaderInput(source=str(source)))
    chunks = DocumentChunker(
        config=ChunkingConfig(chunk_size_tokens=450, chunk_overlap_tokens=60)
    ).chunk_documents(documents)

    assert len(documents) >= 1
    assert len(chunks) >= len(documents)
    assert all(chunk.metadata.source_type == DocumentType.pdf for chunk in chunks)
    assert all(chunk.metadata.page_start is not None for chunk in chunks)
    assert all(chunk.metadata.page_end is not None for chunk in chunks)
    assert all(chunk.metadata.parent_id for chunk in chunks)
    report = ChunkQualityReporter().build(chunks)
    assert report.empty_chunks == 0
    assert report.duplicate_chunks == 0


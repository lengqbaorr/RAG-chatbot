from app.services.vectorstore.models import VectorRecord
from tests.conftest import make_embedded_chunk


class TestVectorRecordFromEmbeddedChunk:
    def test_basic_conversion(self):
        ec = make_embedded_chunk(
            chunk_id="c1",
            document_id="doc_001",
            source_name="report.pdf",
            header_path=["Section A", "Chapter 1"],
        )
        vr = VectorRecord.from_embedded_chunk(ec)

        assert vr.chunk_id == "c1"
        assert vr.document_id == "doc_001"
        assert vr.source_name == "report.pdf"
        assert vr.embedding_provider == "bge-m3"
        assert vr.embedding_model == "BAAI/bge-m3"
        assert vr.embedding_dimension == 4
        assert vr.header_path == ["Section A", "Chapter 1"]
        assert vr.header_path_text == "Section A > Chapter 1"
        assert vr.vector == [0.1, 0.2, 0.3, 0.4]
        assert vr.content_type == "body"
        assert vr.chunk_level == "child"

    def test_parent_child_fields(self):
        ec = make_embedded_chunk(
            chunk_id="child_1",
            parent_id="parent_001",
            child_ids=["child_2", "child_3"],
        )
        vr = VectorRecord.from_embedded_chunk(ec)

        assert vr.parent_id == "parent_001"
        assert vr.child_ids == ["child_2", "child_3"]

    def test_metadata_is_preserved(self):
        ec = make_embedded_chunk(chunk_id="c1", source_name="report.pdf", content_type="heading")
        vr = VectorRecord.from_embedded_chunk(ec)

        assert vr.metadata["source_name"] == "report.pdf"
        assert vr.metadata["content_type"] == "heading"
        assert vr.metadata["chunk_strategy"] == "recursive_token"

    def test_empty_header_path(self):
        ec = make_embedded_chunk(chunk_id="c1", header_path=[])
        vr = VectorRecord.from_embedded_chunk(ec)

        assert vr.header_path == []
        assert vr.header_path_text == ""

    def test_vector_is_copied(self):
        ec = make_embedded_chunk(chunk_id="c1")
        vr = VectorRecord.from_embedded_chunk(ec)

        assert vr.vector == ec.vector
        assert vr.embedding_text == ec.embedding_text
        assert vr.embedding_text_hash == ec.embedding_text_hash

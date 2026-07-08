import pytest
from chromadb import EphemeralClient

from app.services.vectorstore.filters import ChromaFilterBuilder
from app.services.vectorstore.models import VectorRecord
from app.services.vectorstore.providers.chroma_store import ChromaVectorStore


@pytest.fixture
def store():
    return ChromaVectorStore(
        collection_name="test_collection",
        persist_directory="./data/chroma_test",
        embedding_dimension=4,
        distance_metric="cosine",
    )


@pytest.fixture
def records():
    return [
        VectorRecord(
            chunk_id="c1",
            document_id="doc_a",
            source_id="src_a",
            content="Alpha content",
            embedding_text="emb_alpha",
            vector=[0.1, 0.2, 0.3, 0.4],
            metadata={"source_name": "a.pdf"},
            source_name="a.pdf",
            source_type="pdf",
            content_type="body",
            chunk_level="child",
            embedding_provider="bge-m3",
            embedding_model="BAAI/bge-m3",
            embedding_dimension=4,
            embedding_version="v1",
            embedding_text_hash="h1",
        ),
        VectorRecord(
            chunk_id="c2",
            document_id="doc_a",
            source_id="src_a",
            content="Beta content",
            embedding_text="emb_beta",
            vector=[0.5, 0.6, 0.7, 0.8],
            metadata={"source_name": "a.pdf"},
            source_name="a.pdf",
            source_type="pdf",
            content_type="heading",
            chunk_level="child",
            embedding_provider="bge-m3",
            embedding_model="BAAI/bge-m3",
            embedding_dimension=4,
            embedding_version="v1",
            embedding_text_hash="h2",
        ),
        VectorRecord(
            chunk_id="c3",
            document_id="doc_b",
            source_id="src_b",
            content="Gamma content",
            embedding_text="emb_gamma",
            vector=[0.9, 1.0, 1.1, 1.2],
            metadata={"source_name": "b.docx"},
            source_name="b.docx",
            source_type="docx",
            content_type="body",
            chunk_level="parent",
            embedding_provider="bge-m3",
            embedding_model="BAAI/bge-m3",
            embedding_dimension=4,
            embedding_version="v1",
            embedding_text_hash="h3",
        ),
    ]


class TestChromaVectorStore:
    def test_upsert_and_count(self, store, records):
        result = store.upsert(records)
        assert result.upserted_count == 3
        assert store.count() == 3

    def test_upsert_empty(self, store):
        result = store.upsert([])
        assert result.upserted_count == 0

    def test_similarity_search_top_k(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=2,
        )
        assert len(results) == 2

    def test_similarity_search_best_match(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=3,
        )
        assert results[0].chunk_id == "c1"
        assert results[0].score > 0.9

    def test_search_with_filter(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=5,
            filters={"document_id": "doc_a"},
        )
        assert len(results) == 2
        assert all(r.document_id == "doc_a" for r in results)

    def test_search_with_content_type_filter(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=5,
            filters={"content_type": "heading"},
        )
        assert len(results) == 1
        assert results[0].chunk_id == "c2"

    def test_delete_by_document_id(self, store, records):
        store.upsert(records)
        store.delete_by_document_id("doc_a")
        assert store.count() == 1

    def test_delete_by_source_id(self, store, records):
        store.upsert(records)
        result = store.delete_by_source_id("src_a")
        assert result.deleted_count == 2
        assert store.count() == 1

    def test_delete_by_chunk_ids(self, store, records):
        store.upsert(records)
        store.delete_by_chunk_ids(["c1", "c3"])
        assert store.count() == 1
        assert store.get_by_chunk_id("c2") is not None

    def test_get_by_chunk_id(self, store, records):
        store.upsert(records)
        rec = store.get_by_chunk_id("c1")
        assert rec is not None
        assert rec.chunk_id == "c1"
        assert rec.document_id == "doc_a"

    def test_get_by_chunk_id_miss(self, store):
        rec = store.get_by_chunk_id("nonexistent")
        assert rec is None

    def test_stats(self, store, records):
        store.upsert(records)
        stats = store.stats()
        assert stats.total_count == 3
        assert stats.collection_name == "test_collection"
        assert stats.embedding_dimension == 4

    def test_score_range_is_valid(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=3,
        )
        for r in results:
            assert 0.0 <= r.score <= 1.0
            assert r.distance >= 0.0

    def test_search_result_fields(self, store, records):
        store.upsert(records)
        results = store.similarity_search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=1,
        )
        r = results[0]
        assert r.chunk_id == "c1"
        assert r.document_id == "doc_a"
        assert r.score > 0.0
        assert r.distance >= 0.0
        assert r.source_name == "a.pdf"
        assert r.content_type == "body"
        assert r.chunk_level == "child"

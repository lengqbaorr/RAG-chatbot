from unittest.mock import MagicMock

import pytest

from app.services.vectorstore.config import VectorStoreConfig
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreUpsertResult,
)
from app.services.vectorstore.service import VectorStoreService
from app.services.vectorstore.validators import VectorStoreValidationError
from tests.conftest import make_embedded_chunk


class FakeVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self._store: dict[str, VectorRecord] = {}
        self.upsert_called = 0

    def upsert(self, records: list[VectorRecord]) -> VectorStoreUpsertResult:
        self.upsert_called += 1
        for r in records:
            self._store[r.chunk_id] = r
        return VectorStoreUpsertResult(
            total_input=len(records),
            skipped_excluded=0,
            upserted_count=len(records),
            failed_count=0,
            collection_name="test",
        )

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        return []

    def delete_by_document_id(self, document_id: str):
        return MagicMock()

    def delete_by_source_id(self, source_id: str):
        return MagicMock()

    def delete_by_chunk_ids(self, chunk_ids: list[str]):
        return MagicMock()

    def get_by_chunk_id(self, chunk_id: str) -> VectorRecord | None:
        return self._store.get(chunk_id)

    def count(self, filters: dict | None = None) -> int:
        return len(self._store)

    def stats(self):
        return MagicMock()


@pytest.fixture
def config():
    return VectorStoreConfig(
        collection_name="test_coll",
        embedding_model="BAAI/bge-m3",
        embedding_dimension=4,
        include_retrieval_excluded=False,
    )


@pytest.fixture
def store():
    return FakeVectorStore()


@pytest.fixture
def service(config, store):
    return VectorStoreService(config=config, store=store)


class TestVectorStoreService:
    def test_upsert_all_valid(self, service, store):
        chunks = [
            make_embedded_chunk("c1", text="Alpha"),
            make_embedded_chunk("c2", text="Beta"),
        ]
        result = service.upsert_embeddings(chunks)

        assert result.total_input == 2
        assert result.upserted_count == 2
        assert result.skipped_excluded == 0
        assert store.upsert_called == 1

    def test_skips_retrieval_excluded(self, service, store):
        chunks = [
            make_embedded_chunk("c1", text="Alpha", retrieval_excluded=False),
            make_embedded_chunk("c2", text="Beta", retrieval_excluded=True),
            make_embedded_chunk("c3", text="Gamma", retrieval_excluded=False),
        ]
        result = service.upsert_embeddings(chunks)

        assert result.total_input == 3
        assert result.skipped_excluded == 1
        assert result.upserted_count == 2

    def test_include_retrieval_excluded_when_config_true(self, store):
        config = VectorStoreConfig(
            collection_name="test",
            embedding_model="BAAI/bge-m3",
            embedding_dimension=4,
            include_retrieval_excluded=True,
        )
        svc = VectorStoreService(config=config, store=store)
        chunks = [
            make_embedded_chunk("c1", retrieval_excluded=True),
            make_embedded_chunk("c2", retrieval_excluded=False),
        ]
        result = svc.upsert_embeddings(chunks)

        assert result.total_input == 2
        assert result.skipped_excluded == 0
        assert result.upserted_count == 2

    def test_dimension_mismatch_raises(self, store):
        config = VectorStoreConfig(
            collection_name="test",
            embedding_model="BAAI/bge-m3",
            embedding_dimension=999,
        )
        svc = VectorStoreService(config=config, store=store)
        chunks = [make_embedded_chunk("c1", embedding_dimension=4, vector=[0.1, 0.2, 0.3, 0.4])]

        with pytest.raises(VectorStoreValidationError):
            svc.upsert_embeddings(chunks)

    def test_empty_chunks(self, service, store):
        result = service.upsert_embeddings([])
        assert result.total_input == 0
        assert result.upserted_count == 0

    def test_search_delegates_to_store(self, service, store):
        result = service.search(
            query_vector=[0.1, 0.2, 0.3, 0.4],
            top_k=3,
            filters={"content_type": "body"},
        )
        assert isinstance(result, list)

    def test_upsert_collection_name_in_report(self, service):
        chunks = [make_embedded_chunk("c1")]
        result = service.upsert_embeddings(chunks)
        assert result.collection_name == "test_coll"

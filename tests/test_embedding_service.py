from dataclasses import dataclass
from datetime import datetime

import pytest

from app.schemas.chunk import ChunkMetadata, ChunkingStrategy, ContentType, DocumentChunk
from app.schemas.document import DocumentType
from app.services.embedding.cache import SQLiteEmbeddingCache
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.interfaces import EmbeddingProvider
from app.services.embedding.models import EmbeddingInput
from app.services.embedding.service import EmbeddingService
from app.services.embedding.validator import EmbeddingValidationError


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        dimension: int = 4,
        model_name: str = "fake-model",
    ) -> None:
        self._dimension = dimension
        self._model_name = model_name
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [[float(i + j) for j in range(self._dimension)] for i in range(len(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def _make_chunk(
    chunk_id: str = "c1",
    retrieval_excluded: bool = False,
    text: str = "Hello world",
    source_name: str = "test.pdf",
    header_path: list[str] | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=chunk_id,
        document_id="doc_001",
        source_id="src_001",
        text=text,
        chunk_index=0,
        token_count=10,
        content_hash=f"hash_{chunk_id}",
        metadata=ChunkMetadata(
            source_id="src_001",
            source_name=source_name,
            source_type=DocumentType.pdf,
            chunk_index=0,
            token_count=10,
            content_hash=f"hash_{chunk_id}",
            header_path=header_path or [],
            content_type=ContentType.body,
            retrieval_excluded=retrieval_excluded,
            embedding_text_hash="",
            chunk_strategy=ChunkingStrategy.recursive_token,
        ),
    )


@pytest.fixture
def config():
    return EmbeddingConfig(
        provider="fake",
        model_name="fake-model",
        dimension=4,
        batch_size=2,
        embedding_version="v1",
        skip_retrieval_excluded=True,
        cache_enabled=True,
    )


@pytest.fixture
def provider():
    return FakeEmbeddingProvider(dimension=4)


@pytest.fixture
def cache():
    c = SQLiteEmbeddingCache()
    yield c
    c.close()


@pytest.fixture
def service(config, provider, cache):
    return EmbeddingService(config=config, provider=provider, cache=cache)


class TestEmbeddingService:
    def test_happy_path(self, service, provider):
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        result = service.embed_chunks(chunks)

        assert len(result.chunks) == 2
        assert provider.call_count == 1

        for ec in result.chunks:
            assert len(ec.vector) == 4
            assert ec.embedding_provider == "fake"
            assert ec.embedding_model == "fake-model"
            assert ec.embedding_dimension == 4
            assert ec.embedding_version == "v1"
            assert ec.embedded_at is not None

    def test_cache_hit(self, service, provider, cache):
        chunks = [_make_chunk("c1")]
        result1 = service.embed_chunks(chunks)
        assert provider.call_count == 1

        result2 = service.embed_chunks(chunks)
        assert provider.call_count == 1
        assert result2.report.cache_hits == 1
        assert result2.report.cache_misses == 0
        assert result2.report.embedded_count == 0

        assert result1.chunks[0].vector == result2.chunks[0].vector

    def test_cache_miss_then_hit(self, service, provider):
        chunks = [_make_chunk("c1", text="Alpha"), _make_chunk("c2", text="Beta")]
        result1 = service.embed_chunks(chunks)
        assert provider.call_count == 1
        assert result1.report.cache_hits == 0
        assert result1.report.cache_misses == 2

        chunks2 = [_make_chunk("c3", text="Alpha"), _make_chunk("c4", text="Gamma")]
        result2 = service.embed_chunks(chunks2)
        assert provider.call_count == 2
        assert result2.report.cache_hits == 1
        assert result2.report.cache_misses == 1

    def test_retrieval_excluded_filtered(self, service, provider):
        chunks = [
            _make_chunk("c1", retrieval_excluded=False),
            _make_chunk("c2", retrieval_excluded=True),
            _make_chunk("c3", retrieval_excluded=False),
        ]
        result = service.embed_chunks(chunks)

        assert len(result.chunks) == 2
        assert result.report.total_chunks == 3
        assert result.report.excluded_chunks == 1
        assert result.report.embedded_count == 2

        chunk_ids = {ec.chunk_id for ec in result.chunks}
        assert "c2" not in chunk_ids

    def test_retrieval_excluded_skipped_when_disabled(self, provider, cache):
        config = EmbeddingConfig(
            provider="fake",
            model_name="fake-model",
            dimension=4,
            skip_retrieval_excluded=False,
        )
        svc = EmbeddingService(config=config, provider=provider, cache=cache)
        chunks = [
            _make_chunk("c1", retrieval_excluded=True),
            _make_chunk("c2", retrieval_excluded=False),
        ]
        result = svc.embed_chunks(chunks)

        assert len(result.chunks) == 2
        assert result.report.excluded_chunks == 0

    def test_dimension_mismatch_raises(self, provider, cache):
        config = EmbeddingConfig(
            provider="fake",
            model_name="fake-model",
            dimension=999,
            batch_size=2,
        )
        svc = EmbeddingService(config=config, provider=provider, cache=cache)
        chunks = [_make_chunk("c1")]

        with pytest.raises(EmbeddingValidationError):
            svc.embed_chunks(chunks)

    def test_cache_disabled(self, provider):
        config = EmbeddingConfig(
            provider="fake",
            model_name="fake-model",
            dimension=4,
            cache_enabled=False,
        )
        svc = EmbeddingService(config=config, provider=provider, cache=None)
        chunks = [_make_chunk("c1"), _make_chunk("c1")]

        result1 = svc.embed_chunks(chunks)
        assert provider.call_count == 1

        result2 = svc.embed_chunks(chunks)
        assert provider.call_count == 2
        assert result2.report.cache_hits == 0
        assert result2.report.cache_misses == 2

    def test_empty_chunks(self, service, provider):
        result = service.embed_chunks([])
        assert len(result.chunks) == 0
        assert result.report.total_chunks == 0
        assert result.report.embedded_count == 0
        assert provider.call_count == 0

    def test_report_fields(self, service):
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        result = service.embed_chunks(chunks)

        report = result.report
        assert report.total_chunks == 2
        assert report.excluded_chunks == 0
        assert report.cache_hits == 0
        assert report.cache_misses == 2
        assert report.embedded_count == 2
        assert report.provider_name == "fake"
        assert report.model_name == "fake-model"
        assert report.dimension == 4

    def test_batching_multiple_calls(self, service, provider):
        chunks = [_make_chunk(f"c{i}") for i in range(5)]
        result = service.embed_chunks(chunks)

        assert len(result.chunks) == 5
        assert provider.call_count == 3
        assert all(len(ec.vector) == 4 for ec in result.chunks)

    def test_different_texts_different_vectors(self, service):
        chunks = [
            _make_chunk("c1", text="Alpha"),
            _make_chunk("c2", text="Beta"),
        ]
        result = service.embed_chunks(chunks)

        assert result.chunks[0].vector != result.chunks[1].vector

    def test_service_delegates_validation(self, provider):
        config = EmbeddingConfig(
            provider="fake",
            model_name="fake-model",
            dimension=4,
            skip_retrieval_excluded=False,
        )
        svc = EmbeddingService(config=config, provider=provider, cache=None)
        chunks = [_make_chunk("c1", text="valid")]
        result = svc.embed_chunks(chunks)
        assert len(result.chunks) == 1

        bad_provider = FakeEmbeddingProvider(dimension=4)
        bad_config = EmbeddingConfig(
            provider="fake",
            model_name="fake-model",
            dimension=999,
            skip_retrieval_excluded=False,
        )
        bad_svc = EmbeddingService(config=bad_config, provider=bad_provider, cache=None)
        with pytest.raises(EmbeddingValidationError):
            bad_svc.embed_chunks(chunks)

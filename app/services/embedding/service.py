from datetime import datetime

from app.schemas.chunk import DocumentChunk
from app.services.chunking.hashers import stable_hash
from app.services.embedding.batcher import EmbeddingBatcher
from app.services.embedding.cache import EmbeddingCache
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.interfaces import EmbeddingProvider
from app.services.embedding.models import (
    EmbeddedChunk,
    EmbeddingBatchResult,
    EmbeddingInput,
    EmbeddingReport,
)
from app.services.embedding.text_builder import EmbeddingTextBuilder
from app.services.embedding.validator import EmbeddingValidator


class EmbeddingService:
    def __init__(
        self,
        config: EmbeddingConfig,
        provider: EmbeddingProvider,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self._config = config
        self._provider = provider
        self._cache = cache
        self._text_builder = EmbeddingTextBuilder()
        self._batcher = EmbeddingBatcher(batch_size=config.batch_size)
        self._validator = EmbeddingValidator()

    def embed_chunks(
        self, chunks: list[DocumentChunk]
    ) -> EmbeddingBatchResult:
        total = len(chunks)

        if self._config.skip_retrieval_excluded:
            active = [
                c for c in chunks
                if c.metadata is None or not c.metadata.retrieval_excluded
            ]
            excluded = total - len(active)
        else:
            active = list(chunks)
            excluded = 0

        inputs = self._build_inputs(active)

        cache_hits: list[EmbeddedChunk] = []
        cache_misses: list[EmbeddingInput] = []

        self._split_cache(inputs, cache_hits, cache_misses)

        new_embedded: list[EmbeddedChunk] = []
        batches = self._batcher.batch(cache_misses)

        for batch in batches:
            texts = [inp.embedding_text for inp in batch]
            vectors = self._provider.embed_documents(texts)
            self._validator.validate_batch(
                vectors, batch, self._config.dimension
            )
            for vector, inp in zip(vectors, batch):
                self._save_to_cache(inp.embedding_text_hash, vector)
                new_embedded.append(
                    self._build_embedded_chunk(inp, vector)
                )

        all_embedded = cache_hits + new_embedded

        report = EmbeddingReport(
            total_chunks=total,
            excluded_chunks=excluded,
            cache_hits=len(cache_hits),
            cache_misses=len(cache_misses),
            embedded_count=len(new_embedded),
            provider_name=self._provider.provider_name,
            model_name=self._provider.model_name,
            dimension=self._provider.dimension,
        )

        return EmbeddingBatchResult(chunks=all_embedded, report=report)

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("query text must not be empty")
        vector = self._provider.embed_query(text)
        self._validator.validate_query_vector(vector, self._config.dimension)
        return vector

    def _build_inputs(
        self, chunks: list[DocumentChunk]
    ) -> list[EmbeddingInput]:
        inputs: list[EmbeddingInput] = []
        for chunk in chunks:
            if chunk.metadata is None:
                continue
            embedding_text = self._text_builder.build(chunk)
            text_hash = stable_hash(embedding_text)
            inputs.append(
                EmbeddingInput(
                    chunk=chunk,
                    embedding_text=embedding_text,
                    embedding_text_hash=text_hash,
                )
            )
        return inputs

    def _split_cache(
        self,
        inputs: list[EmbeddingInput],
        hits: list[EmbeddedChunk],
        misses: list[EmbeddingInput],
    ) -> None:
        if not self._config.cache_enabled or self._cache is None:
            misses.extend(inputs)
            return

        for inp in inputs:
            cache_key = self._cache.build_key(
                self._provider.provider_name,
                self._provider.model_name,
                self._provider.dimension,
                inp.embedding_text_hash,
            )
            if self._cache.exists(cache_key):
                vector = self._cache.get(cache_key)
                if vector is not None:
                    hits.append(
                        self._build_embedded_chunk(inp, vector)
                    )
                    continue
            misses.append(inp)

    def _build_embedded_chunk(
        self,
        inp: EmbeddingInput,
        vector: list[float],
    ) -> EmbeddedChunk:
        return EmbeddedChunk(
            chunk_id=inp.chunk.chunk_id,
            document_id=inp.chunk.document_id,
            content=inp.chunk.text,
            embedding_text=inp.embedding_text,
            embedding_text_hash=inp.embedding_text_hash,
            vector=vector,
            metadata=inp.chunk.metadata,
            embedding_provider=self._provider.provider_name,
            embedding_model=self._provider.model_name,
            embedding_dimension=self._provider.dimension,
            embedding_version=self._config.embedding_version,
            embedded_at=datetime.utcnow(),
        )

    def _save_to_cache(
        self, text_hash: str, vector: list[float]
    ) -> None:
        if not self._config.cache_enabled or self._cache is None:
            return
        cache_key = self._cache.build_key(
            self._provider.provider_name,
            self._provider.model_name,
            self._provider.dimension,
            text_hash,
        )
        self._cache.set(cache_key, vector)

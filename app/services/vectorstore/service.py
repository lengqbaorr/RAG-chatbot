from app.services.embedding.models import EmbeddedChunk
from app.services.vectorstore.config import VectorStoreConfig
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreUpsertResult,
)
from app.services.vectorstore.validators import VectorStoreValidator


class VectorStoreService:
    def __init__(
        self,
        config: VectorStoreConfig,
        store: BaseVectorStore,
    ) -> None:
        self._config = config
        self._store = store
        self._validator = VectorStoreValidator()

    def upsert_embeddings(
        self, chunks: list[EmbeddedChunk]
    ) -> VectorStoreUpsertResult:
        total = len(chunks)

        if not chunks:
            return VectorStoreUpsertResult(
                total_input=0,
                skipped_excluded=0,
                upserted_count=0,
                failed_count=0,
                collection_name=self._config.collection_name,
            )

        if not self._config.include_retrieval_excluded:
            active = [
                c for c in chunks
                if c.metadata is None or not c.metadata.retrieval_excluded
            ]
            skipped = total - len(active)
        else:
            active = list(chunks)
            skipped = 0

        if not active:
            return VectorStoreUpsertResult(
                total_input=total,
                skipped_excluded=skipped,
                upserted_count=0,
                failed_count=0,
                collection_name=self._config.collection_name,
            )

        records = [VectorRecord.from_embedded_chunk(c) for c in active]

        self._validator.validate_records(
            records,
            expected_model=self._config.embedding_model,
            expected_dimension=self._config.embedding_dimension,
        )

        result = self._store.upsert(records)

        result.total_input = total
        result.skipped_excluded = skipped
        result.collection_name = self._config.collection_name

        return result

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        return self._store.similarity_search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )

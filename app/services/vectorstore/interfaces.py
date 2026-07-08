from abc import ABC, abstractmethod

from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreDeleteResult,
    VectorStoreStats,
    VectorStoreUpsertResult,
)


class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> VectorStoreUpsertResult:
        ...

    @abstractmethod
    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[VectorSearchResult]:
        ...

    @abstractmethod
    def delete_by_document_id(
        self, document_id: str
    ) -> VectorStoreDeleteResult:
        ...

    @abstractmethod
    def delete_by_source_id(
        self, source_id: str
    ) -> VectorStoreDeleteResult:
        ...

    @abstractmethod
    def delete_by_chunk_ids(
        self, chunk_ids: list[str]
    ) -> VectorStoreDeleteResult:
        ...

    @abstractmethod
    def get_by_chunk_id(self, chunk_id: str) -> VectorRecord | None:
        ...

    @abstractmethod
    def count(self, filters: dict | None = None) -> int:
        ...

    @abstractmethod
    def stats(self) -> VectorStoreStats:
        ...

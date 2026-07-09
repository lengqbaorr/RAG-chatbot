from app.services.vectorstore.config import VectorStoreConfig
from app.services.vectorstore.filters import ChromaFilterBuilder, FilterBuilderError
from app.services.vectorstore.interfaces import BaseVectorStore
from app.services.vectorstore.models import (
    VectorRecord,
    VectorSearchResult,
    VectorStoreDeleteResult,
    VectorStoreStats,
    VectorStoreUpsertResult,
)
from app.services.vectorstore.service import VectorStoreService
from app.services.vectorstore.validators import (
    VectorStoreValidationError,
    VectorStoreValidator,
)


def __getattr__(name: str):
    if name in {"ChromaVectorStore", "ChromaVectorStoreError"}:
        from app.services.vectorstore.providers.chroma_store import (
            ChromaVectorStore,
            ChromaVectorStoreError,
        )

        return {
            "ChromaVectorStore": ChromaVectorStore,
            "ChromaVectorStoreError": ChromaVectorStoreError,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseVectorStore",
    "ChromaFilterBuilder",
    "ChromaVectorStore",
    "ChromaVectorStoreError",
    "FilterBuilderError",
    "VectorRecord",
    "VectorSearchResult",
    "VectorStoreConfig",
    "VectorStoreDeleteResult",
    "VectorStoreService",
    "VectorStoreStats",
    "VectorStoreUpsertResult",
    "VectorStoreValidationError",
    "VectorStoreValidator",
]

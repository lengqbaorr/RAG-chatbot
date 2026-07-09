from app.services.embedding.batcher import EmbeddingBatcher
from app.services.embedding.cache import EmbeddingCache, SQLiteEmbeddingCache
from app.services.embedding.config import EmbeddingConfig
from app.services.embedding.interfaces import EmbeddingProvider
from app.services.embedding.models import (
    EmbeddedChunk,
    EmbeddingBatchResult,
    EmbeddingInput,
    EmbeddingReport,
)
from app.services.embedding.service import EmbeddingService
from app.services.embedding.text_builder import EmbeddingTextBuilder
from app.services.embedding.validator import (
    EmbeddingValidationError,
    EmbeddingValidator,
)


def __getattr__(name: str):
    if name in {"BGEM3EmbeddingError", "BGEM3EmbeddingProvider"}:
        from app.services.embedding.providers.bge_m3_provider import (
            BGEM3EmbeddingError,
            BGEM3EmbeddingProvider,
        )

        return {
            "BGEM3EmbeddingError": BGEM3EmbeddingError,
            "BGEM3EmbeddingProvider": BGEM3EmbeddingProvider,
        }[name]
    if name in {"OpenAIEmbeddingError", "OpenAIEmbeddingProvider"}:
        from app.services.embedding.providers.openai_provider import (
            OpenAIEmbeddingError,
            OpenAIEmbeddingProvider,
        )

        return {
            "OpenAIEmbeddingError": OpenAIEmbeddingError,
            "OpenAIEmbeddingProvider": OpenAIEmbeddingProvider,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BGEM3EmbeddingError",
    "BGEM3EmbeddingProvider",
    "EmbeddedChunk",
    "EmbeddingBatchResult",
    "EmbeddingBatcher",
    "EmbeddingCache",
    "EmbeddingConfig",
    "EmbeddingInput",
    "EmbeddingProvider",
    "EmbeddingReport",
    "EmbeddingService",
    "EmbeddingTextBuilder",
    "EmbeddingValidationError",
    "EmbeddingValidator",
    "OpenAIEmbeddingError",
    "OpenAIEmbeddingProvider",
    "SQLiteEmbeddingCache",
]

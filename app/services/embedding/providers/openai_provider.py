import logging
import warnings

from openai import OpenAI
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.services.embedding.interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingError(Exception):
    pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        api_key: str | None = None,
    ) -> None:
        resolved_key = api_key or settings.openai_api_key
        self._client = OpenAI(api_key=resolved_key)
        self._model = model
        self._dimension = dimension

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimension,
        )

        if len(response.data) != len(texts):
            msg = (
                f"Response has {len(response.data)} embeddings, "
                f"expected {len(texts)}"
            )
            warnings.warn(msg)
            raise OpenAIEmbeddingError(msg)

        sorted_data = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in sorted_data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

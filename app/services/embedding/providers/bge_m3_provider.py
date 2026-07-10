import logging

from sentence_transformers import SentenceTransformer

from app.services.embedding.interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)


class BGEM3EmbeddingError(Exception):
    pass


class BGEM3EmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        batch_size: int = 64,
        cache_folder: str | None = None,
        local_files_only: bool = False,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._cache_folder = cache_folder
        self._local_files_only = local_files_only
        self._model: SentenceTransformer | None = None

    @property
    def provider_name(self) -> str:
        return "bge-m3"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._get_model().get_embedding_dimension()

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info("Loading BGE-M3 model: %s (device=%s)", self._model_name, self._device)
            try:
                self._model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                    cache_folder=self._cache_folder,
                    local_files_only=self._local_files_only,
                )
            except Exception as exc:
                mode = "local cache only" if self._local_files_only else "local cache or Hugging Face"
                raise BGEM3EmbeddingError(
                    f"Could not load embedding model '{self._model_name}' using {mode}. "
                    "Set EMBEDDING_LOCAL_FILES_ONLY=false to allow the first online download, "
                    "then set it back to true for offline startup."
                ) from exc
        return self._model

    def preload(self) -> int:
        model = self._get_model()
        return model.get_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

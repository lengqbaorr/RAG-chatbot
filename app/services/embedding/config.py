from dataclasses import dataclass, field


@dataclass
class EmbeddingConfig:
    provider: str = "bge-m3"
    model_name: str = "BAAI/bge-m3"
    dimension: int = 1024
    batch_size: int = 64
    embedding_version: str = "v1"
    skip_retrieval_excluded: bool = True
    cache_enabled: bool = True
    cache_db_path: str | None = None
    max_retries: int = 3

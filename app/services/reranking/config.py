from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RerankerConfig:
    provider: str = "bge"
    model_name: str = "BAAI/bge-reranker-base"
    device: str = "cpu"
    batch_size: int = 16
    cache_folder: str | None = None
    local_files_only: bool = False
    max_length: int = 512

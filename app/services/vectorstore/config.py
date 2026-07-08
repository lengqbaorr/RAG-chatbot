from dataclasses import dataclass


@dataclass
class VectorStoreConfig:
    provider: str = "chroma"
    collection_name: str = "personal_docs_bge_m3_1024"
    persist_directory: str = "./data/chroma"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    distance_metric: str = "cosine"
    include_retrieval_excluded: bool = False

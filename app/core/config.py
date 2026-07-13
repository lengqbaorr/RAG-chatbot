from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG Chatbot"
    app_version: str = "0.1.0"
    environment: str = "local"
    app_env: str = "dev"
    debug: bool = True
    tesseract_cmd: str | None = None
    ocr_languages: str = "eng"
    http_timeout_seconds: float = 20.0
    http_user_agent: str = "rag-chatbot/0.1.0"
    openai_api_key: str | None = None
    chroma_path: str = "./data/chroma"
    chroma_collection: str = "personal_docs_bge_m3_1024"
    metadata_db_path: str = "./data/metadata.db"
    embedding_provider: str = "bge-m3"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    embedding_cache_path: str = "./data/embeddings.db"
    embedding_local_files_only: bool = True
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    upload_dir: str = "./data/raw"
    max_upload_mb: int = 50
    allowed_upload_extensions: str = "pdf,docx,txt,md,png,jpg,jpeg,bmp,gif,tif,tiff,webp"
    duplicate_policy: str = "skip"
    default_retrieval_strategy: str = "parent_child"
    default_top_k: int = 3
    default_fetch_k: int = 8
    default_min_score: float = 0.70
    retrieval_fallback_min_score: float = 0.55
    retrieval_fallback_enabled: bool = True
    reranker_enabled: bool = False
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_device: str = "cpu"
    reranker_local_files_only: bool = True
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    disable_startup: bool = False
    auth_enabled: bool = False
    auth_local_username: str = "local"
    auth_local_password: str = "change-me"
    auth_secret_key: str = "change-me-local-secret"
    auth_token_ttl_minutes: int = 1440

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG Chatbot"
    app_version: str = "0.1.0"
    environment: str = "local"
    debug: bool = True
    tesseract_cmd: str | None = None
    ocr_languages: str = "eng"
    http_timeout_seconds: float = 20.0
    http_user_agent: str = "rag-chatbot/0.1.0"
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

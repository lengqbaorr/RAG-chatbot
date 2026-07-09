from __future__ import annotations

from dataclasses import dataclass

from app.services.llm.service import LLMService
from app.services.vectorstore.interfaces import BaseVectorStore


@dataclass(frozen=True)
class HealthStatus:
    app: str
    embedding_service: str
    vector_store: str
    llm_provider: str
    collection: str | None
    collection_count: int
    ready: bool


class HealthService:
    def __init__(
        self,
        *,
        vector_store: BaseVectorStore | None = None,
        llm_service: LLMService | None = None,
        embedding_service: object | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.embedding_service = embedding_service

    def check(self) -> HealthStatus:
        collection = None
        count = 0
        vector_status = "unavailable"
        if self.vector_store is not None:
            try:
                stats = self.vector_store.stats()
                collection = stats.collection_name
                count = stats.total_count
                vector_status = "ok"
            except Exception:
                vector_status = "error"

        embedding_status = "ok" if self.embedding_service is not None else "unavailable"
        llm_provider = self.llm_service.config.provider if self.llm_service is not None else "unavailable"
        ready = embedding_status == "ok" and vector_status == "ok" and llm_provider != "unavailable"
        return HealthStatus(
            app="ok",
            embedding_service=embedding_status,
            vector_store=vector_status,
            llm_provider=llm_provider,
            collection=collection,
            collection_count=count,
            ready=ready,
        )

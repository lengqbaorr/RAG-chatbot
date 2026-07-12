from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.core.config import Settings
from app.services.settings.models import RuntimeSettings, UserSettingsUpdate
from app.services.settings.repository import SettingsRepository


class SettingsService:
    USER_SETTING_KEYS = {
        "llm_model",
        "llm_temperature",
        "llm_max_tokens",
        "retrieval_strategy",
        "top_k",
        "fetch_k",
        "min_score",
        "reranker_enabled",
        "reranker_model",
    }

    def __init__(self, *, repository: SettingsRepository, config: Settings) -> None:
        self.repository = repository
        self.config = config

    def get_runtime_settings(self, *, owner: str = "local") -> RuntimeSettings:
        values = self._defaults()
        values.update(self._validated_overrides(self.repository.get_settings(owner=owner)))
        return RuntimeSettings(**values)

    def update_settings(
        self,
        update: UserSettingsUpdate,
        *,
        owner: str = "local",
    ) -> RuntimeSettings:
        current = self.repository.get_settings(owner=owner)
        patch = {key: value for key, value in asdict(update).items() if value is not None}
        current.update(patch)
        current = self._validated_overrides(current)
        self.repository.save_settings(current, owner=owner)
        return self.get_runtime_settings(owner=owner)

    def reset_settings(self, *, owner: str = "local") -> RuntimeSettings:
        self.repository.save_settings({}, owner=owner)
        return self.get_runtime_settings(owner=owner)

    def _defaults(self) -> dict[str, Any]:
        return {
            "app_name": self.config.app_name,
            "app_version": self.config.app_version,
            "environment": self.config.environment,
            "auth_enabled": self.config.auth_enabled,
            "llm_provider": self.config.llm_provider,
            "llm_model": self.config.llm_model,
            "llm_temperature": self.config.llm_temperature,
            "llm_max_tokens": self.config.llm_max_tokens,
            "retrieval_strategy": self.config.default_retrieval_strategy,
            "top_k": self.config.default_top_k,
            "fetch_k": self.config.default_fetch_k,
            "min_score": self.config.default_min_score,
            "reranker_enabled": self.config.reranker_enabled,
            "reranker_model": self.config.reranker_model,
            "embedding_provider": self.config.embedding_provider,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": self.config.embedding_dimension,
            "chroma_collection": self.config.chroma_collection,
        }

    def _validated_overrides(self, values: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key in self.USER_SETTING_KEYS:
            if key in values:
                clean[key] = values[key]
        if "retrieval_strategy" in clean and clean["retrieval_strategy"] not in {"dense", "parent_child"}:
            clean.pop("retrieval_strategy")
        return clean

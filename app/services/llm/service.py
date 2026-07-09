from __future__ import annotations

import logging
import time

from app.services.llm.config import LLMConfig
from app.services.llm.interfaces import BaseLLMProvider
from app.services.llm.models import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    pass


class LLMService:
    def __init__(
        self,
        *,
        config: LLMConfig | None = None,
        providers: dict[str, BaseLLMProvider] | None = None,
    ) -> None:
        self.config = config or LLMConfig()
        self.providers = providers or self._build_default_providers()

    def generate(
        self,
        request: LLMRequest,
        *,
        provider_name: str | None = None,
    ) -> LLMResponse:
        selected_provider = provider_name or self.config.provider
        provider = self.providers.get(selected_provider)
        if provider is None:
            raise LLMServiceError(f"Unsupported LLM provider: {selected_provider}")

        effective_request = request.model_copy(
            update={
                "model": request.model or self.config.model or provider.default_model,
                "temperature": (
                    request.temperature
                    if request.temperature is not None
                    else self.config.temperature
                ),
                "max_tokens": request.max_tokens or self.config.max_tokens,
            }
        )

        started = time.perf_counter()
        try:
            response = provider.generate(effective_request)
        except Exception:
            logger.exception("LLM provider failed: %s", selected_provider)
            raise

        latency = response.latency or (time.perf_counter() - started)
        return response.model_copy(update={"latency": latency})

    def _build_default_providers(self) -> dict[str, BaseLLMProvider]:
        from app.services.llm.providers.gemini_provider import GeminiProvider
        from app.services.llm.providers.ollama_provider import OllamaProvider
        from app.services.llm.providers.openrouter_provider import OpenRouterProvider

        return {
            "gemini": GeminiProvider(timeout_seconds=self.config.timeout_seconds),
            "openrouter": OpenRouterProvider(timeout_seconds=self.config.timeout_seconds),
            "ollama": OllamaProvider(timeout_seconds=self.config.timeout_seconds),
        }

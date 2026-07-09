from app.services.llm.config import LLMConfig
from app.services.llm.interfaces import BaseLLMProvider
from app.services.llm.models import (
    LLMGenerationConfig,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)
from app.services.llm.service import LLMService, LLMServiceError


def __getattr__(name: str):
    if name in {"GeminiProvider", "GeminiProviderError"}:
        from app.services.llm.providers.gemini_provider import GeminiProvider, GeminiProviderError

        return {"GeminiProvider": GeminiProvider, "GeminiProviderError": GeminiProviderError}[name]
    if name in {"OpenRouterProvider", "OpenRouterProviderError"}:
        from app.services.llm.providers.openrouter_provider import (
            OpenRouterProvider,
            OpenRouterProviderError,
        )

        return {
            "OpenRouterProvider": OpenRouterProvider,
            "OpenRouterProviderError": OpenRouterProviderError,
        }[name]
    if name in {"OllamaProvider", "OllamaProviderError"}:
        from app.services.llm.providers.ollama_provider import OllamaProvider, OllamaProviderError

        return {"OllamaProvider": OllamaProvider, "OllamaProviderError": OllamaProviderError}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseLLMProvider",
    "GeminiProvider",
    "GeminiProviderError",
    "LLMConfig",
    "LLMGenerationConfig",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "LLMService",
    "LLMServiceError",
    "LLMUsage",
    "OllamaProvider",
    "OllamaProviderError",
    "OpenRouterProvider",
    "OpenRouterProviderError",
]

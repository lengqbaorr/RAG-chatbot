from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: int = 60
    enable_fallback: bool = False
    fallback_providers: tuple[str, ...] = ("openrouter", "ollama")

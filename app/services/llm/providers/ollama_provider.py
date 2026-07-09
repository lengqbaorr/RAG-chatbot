from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
from typing import Any

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.llm.interfaces import BaseLLMProvider
from app.services.llm.models import LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)


class OllamaProviderError(Exception):
    pass


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        load_dotenv()
        self._model = model or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        model = request.model or self.default_model
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        started = time.perf_counter()
        raw = self._post(f"{self._base_url}/api/chat", payload)
        latency = time.perf_counter() - started
        return self._parse_response(raw, model=model, latency=latency)

    def stream(self, request: LLMRequest) -> Iterator[str]:
        del request
        raise NotImplementedError("Ollama streaming is not implemented in the baseline provider")

    @retry(
        retry=retry_if_exception_type((requests.RequestException, OllamaProviderError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(url, json=payload, timeout=self._timeout_seconds)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error("Ollama request failed: %s", response.text[:1000])
            raise OllamaProviderError("Ollama request failed") from exc
        return response.json()

    def _parse_response(self, raw: dict[str, Any], *, model: str, latency: float) -> LLMResponse:
        prompt_tokens = raw.get("prompt_eval_count")
        completion_tokens = raw.get("eval_count")
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(
                prompt_tokens + completion_tokens
                if prompt_tokens is not None and completion_tokens is not None
                else None
            ),
        )
        return LLMResponse(
            text=(raw.get("message", {}).get("content") or "").strip(),
            model=model,
            provider=self.provider_name,
            usage=usage,
            latency=latency,
            finish_reason="stop" if raw.get("done") else None,
            raw_response=raw,
        )

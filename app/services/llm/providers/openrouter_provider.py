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


class OpenRouterProviderError(Exception):
    pass


class OpenRouterProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "qwen/qwen3-8b",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 60,
    ) -> None:
        load_dotenv()
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def default_model(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise OpenRouterProviderError("Missing OPENROUTER_API_KEY")

        model = request.model or self.default_model
        payload = {
            "model": model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        started = time.perf_counter()
        raw = self._post(f"{self._base_url}/chat/completions", payload)
        latency = time.perf_counter() - started
        return self._parse_response(raw, model=model, latency=latency)

    def stream(self, request: LLMRequest) -> Iterator[str]:
        del request
        raise NotImplementedError("OpenRouter streaming is not implemented in the baseline provider")

    @retry(
        retry=retry_if_exception_type((requests.RequestException, OpenRouterProviderError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        site_url = os.getenv("OPENROUTER_SITE_URL")
        app_name = os.getenv("OPENROUTER_APP_NAME")
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name

        response = requests.post(url, headers=headers, json=payload, timeout=self._timeout_seconds)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error("OpenRouter request failed: %s", response.text[:1000])
            raise OpenRouterProviderError("OpenRouter request failed") from exc
        return response.json()

    def _parse_response(self, raw: dict[str, Any], *, model: str, latency: float) -> LLMResponse:
        choices = raw.get("choices") or []
        if not choices:
            raise OpenRouterProviderError("OpenRouter response did not include choices")

        choice = choices[0]
        usage_raw = raw.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_raw.get("prompt_tokens"),
            completion_tokens=usage_raw.get("completion_tokens"),
            total_tokens=usage_raw.get("total_tokens"),
        )
        return LLMResponse(
            text=(choice.get("message", {}).get("content") or "").strip(),
            model=raw.get("model") or model,
            provider=self.provider_name,
            usage=usage,
            latency=latency,
            finish_reason=choice.get("finish_reason"),
            raw_response=raw,
        )

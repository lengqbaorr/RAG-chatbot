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


class GeminiProviderError(Exception):
    pass


class GeminiTransientError(GeminiProviderError):
    pass


class GeminiProvider(BaseLLMProvider):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: int = 60,
    ) -> None:
        load_dotenv()
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise GeminiProviderError("Missing GEMINI_API_KEY or GOOGLE_API_KEY")

        model = request.model or self.default_model
        payload = self._build_payload(request)
        url = f"{self._base_url}/models/{model}:generateContent"
        started = time.perf_counter()
        raw = self._post(url, payload)
        latency = time.perf_counter() - started
        return self._parse_response(raw, model=model, latency=latency)

    def stream(self, request: LLMRequest) -> Iterator[str]:
        del request
        raise NotImplementedError("Gemini streaming is not implemented in the baseline provider")

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, GeminiTransientError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            url,
            headers={"x-goog-api-key": self._api_key or ""},
            json=payload,
            timeout=self._timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error("Gemini request failed: %s", response.text[:1000])
            status = response.status_code
            if status in {429, 500, 502, 503, 504}:
                raise GeminiTransientError(f"Gemini transient request failure with HTTP {status}") from None
            raise GeminiProviderError(f"Gemini request failed with HTTP {status}") from None
        return response.json()

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "system":
                system_parts.append({"text": message.content})
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        return payload

    def _parse_response(self, raw: dict[str, Any], *, model: str, latency: float) -> LLMResponse:
        candidates = raw.get("candidates") or []
        if not candidates:
            raise GeminiProviderError("Gemini response did not include candidates")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        usage_raw = raw.get("usageMetadata", {})
        usage = LLMUsage(
            prompt_tokens=usage_raw.get("promptTokenCount"),
            completion_tokens=usage_raw.get("candidatesTokenCount"),
            total_tokens=usage_raw.get("totalTokenCount"),
        )
        return LLMResponse(
            text=text,
            model=model,
            provider=self.provider_name,
            usage=usage,
            latency=latency,
            finish_reason=candidate.get("finishReason"),
            raw_response=raw,
        )

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterator
from typing import Any

import requests
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.llm.interfaces import BaseLLMProvider
from app.services.llm.models import LLMRequest, LLMResponse, LLMStreamChunk, LLMUsage

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

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamChunk]:
        if not self._api_key:
            raise GeminiProviderError("Missing GEMINI_API_KEY or GOOGLE_API_KEY")

        model = request.model or self.default_model
        payload = self._build_payload(request)
        url = f"{self._base_url}/models/{model}:streamGenerateContent?alt=sse"
        response = self._open_stream(url, payload)
        try:
            data_lines: list[str] = []
            for raw_line in response.iter_lines(decode_unicode=False):
                line = (
                    raw_line.decode("utf-8")
                    if isinstance(raw_line, bytes)
                    else raw_line
                )
                if line == "":
                    if data_lines:
                        yield self._decode_stream_event(data_lines, model=model)
                        data_lines.clear()
                    continue
                if line.startswith(":"):
                    continue
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())
                elif data_lines:
                    # Gemini may pretty-print JSON continuation lines without
                    # repeating the SSE data prefix.
                    data_lines.append(line)
            if data_lines:
                yield self._decode_stream_event(data_lines, model=model)
        finally:
            response.close()

    def _decode_stream_event(
        self,
        data_lines: list[str],
        *,
        model: str,
    ) -> LLMStreamChunk:
        raw_data = self._join_json_fragments(data_lines).strip()
        try:
            raw = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            if "Invalid control character" in str(exc):
                # Be tolerant of control characters emitted inside streamed
                # text while keeping normal JSON parsing strict by default.
                try:
                    raw = json.loads(raw_data, strict=False)
                except json.JSONDecodeError:
                    pass
                else:
                    return self._parse_stream_chunk(raw, model=model)
            logger.error(
                "Gemini stream returned malformed event (characters=%s)",
                len(raw_data),
            )
            raise GeminiProviderError("Gemini stream returned invalid JSON") from exc
        return self._parse_stream_chunk(raw, model=model)

    @staticmethod
    def _join_json_fragments(fragments: list[str]) -> str:
        parts: list[str] = []
        in_string = False
        escaped = False
        for index, fragment in enumerate(fragments):
            if index:
                # Some Gemini SSE responses wrap a text value across physical
                # lines. A literal newline is invalid inside JSON strings.
                parts.append("\\n" if in_string else "\n")
            parts.append(fragment)
            for char in fragment:
                if escaped:
                    escaped = False
                    continue
                if char == "\\" and in_string:
                    escaped = True
                    continue
                if char == '"':
                    in_string = not in_string
        return "".join(parts)

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, GeminiTransientError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _open_stream(self, url: str, payload: dict[str, Any]) -> requests.Response:
        response = requests.post(
            url,
            headers={"x-goog-api-key": self._api_key or ""},
            json=payload,
            timeout=self._timeout_seconds,
            stream=True,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.error("Gemini stream request failed: %s", response.text[:1000])
            status = response.status_code
            response.close()
            if status in {429, 500, 502, 503, 504}:
                raise GeminiTransientError(
                    f"Gemini transient stream failure with HTTP {status}"
                ) from None
            raise GeminiProviderError(f"Gemini stream failed with HTTP {status}") from None
        return response

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

    def _parse_stream_chunk(self, raw: dict[str, Any], *, model: str) -> LLMStreamChunk:
        candidates = raw.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts)
        usage_raw = raw.get("usageMetadata", {})
        return LLMStreamChunk(
            text=text,
            model=model,
            provider=self.provider_name,
            usage=LLMUsage(
                prompt_tokens=usage_raw.get("promptTokenCount"),
                completion_tokens=usage_raw.get("candidatesTokenCount"),
                total_tokens=usage_raw.get("totalTokenCount"),
            ),
            finish_reason=candidate.get("finishReason"),
        )

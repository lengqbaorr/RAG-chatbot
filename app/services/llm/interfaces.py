from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from app.services.llm.models import LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        ...

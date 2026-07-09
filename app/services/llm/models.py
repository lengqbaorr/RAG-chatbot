from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class LLMMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class LLMGenerationConfig(BaseModel):
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False


class LLMRequest(BaseModel):
    messages: list[LLMMessage] = Field(..., min_length=1)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_messages(self) -> "LLMRequest":
        if not any(message.content.strip() for message in self.messages):
            raise ValueError("LLMRequest must include at least one non-empty message")
        return self


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency: float = Field(default=0.0, ge=0.0)
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None

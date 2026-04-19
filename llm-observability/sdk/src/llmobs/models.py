from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class LLMObservation(BaseModel):
    prompt: str
    response: str
    model: str
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost: float = Field(ge=0)
    prompt_template_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OpenAIChatResponse(BaseModel):
    content: str
    usage: dict[str, int]
    raw: dict[str, Any]

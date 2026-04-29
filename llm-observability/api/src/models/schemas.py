from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestIngestPayload(BaseModel):
    prompt: str
    response: str
    model: str
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost: float = Field(ge=0)
    prompt_template_id: UUID | None = None


class RequestOut(BaseModel):
    id: UUID
    prompt: str
    response: str
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    prompt_template_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class QualityOut(BaseModel):
    id: UUID
    request_id: UUID
    score: float
    feedback: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateIn(BaseModel):
    name: str
    version: str
    template_text: str


class PromptTemplateOut(BaseModel):
    id: UUID
    name: str
    version: str
    template_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class DriftMetricOut(BaseModel):
    id: UUID
    metric_name: str
    model: str
    prompt_template_id: UUID | None
    baseline_value: float
    recent_value: float
    delta_pct: float | None
    detected_at: datetime

    class Config:
        from_attributes = True

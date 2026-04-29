import random
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.config import settings
from src.models.entities import LLMRequest, PromptTemplate, QualityScore
from src.models.schemas import PromptTemplateIn, RequestIngestPayload
from src.services.metrics_service import record_request_metrics


def ingest_request(db: Session, payload: RequestIngestPayload) -> LLMRequest:
    row = LLMRequest(**payload.model_dump())
    db.add(row)
    db.flush()

    sampled = random.random() < settings.quality_sample_rate
    db.execute(
        text(
            """
            INSERT INTO quality_evaluation_queue (request_id, sampled, processed)
            VALUES (:request_id, :sampled, FALSE)
            ON CONFLICT (request_id) DO UPDATE
            SET sampled = EXCLUDED.sampled
            """
        ),
        {"request_id": row.id, "sampled": sampled},
    )

    record_request_metrics(
        model=row.model,
        latency_ms=row.latency_ms,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        cost=row.cost,
        prompt_version=row.prompt_version,
    )
    db.commit()
    db.refresh(row)
    return row


def list_requests(db: Session, limit: int, offset: int, prompt_version: str | None = None) -> list[LLMRequest]:
    stmt = select(LLMRequest)
    if prompt_version is not None:
        stmt = stmt.where(LLMRequest.prompt_version == prompt_version)
    stmt = stmt.order_by(LLMRequest.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def list_quality_scores(
    db: Session,
    limit: int,
    offset: int,
    prompt_version: str | None = None,
) -> list[QualityScore]:
    stmt = select(QualityScore).join(LLMRequest, LLMRequest.id == QualityScore.request_id)
    if prompt_version is not None:
        stmt = stmt.where(LLMRequest.prompt_version == prompt_version)
    stmt = stmt.order_by(QualityScore.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def list_prompt_templates(db: Session, limit: int, offset: int) -> list[PromptTemplate]:
    stmt = select(PromptTemplate).order_by(PromptTemplate.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def create_prompt_template(db: Session, payload: PromptTemplateIn) -> PromptTemplate:
    row = PromptTemplate(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def average_quality_for_template(db: Session, prompt_template_id: str, n: int) -> float | None:
    subquery = (
        select(QualityScore.score)
        .join(LLMRequest, LLMRequest.id == QualityScore.request_id)
        .where(LLMRequest.prompt_template_id == prompt_template_id)
        .order_by(QualityScore.created_at.desc())
        .limit(n)
        .subquery()
    )
    avg_stmt = select(func.avg(subquery.c.score))
    return db.scalar(avg_stmt)


def now_utc() -> datetime:
    return datetime.now(UTC)

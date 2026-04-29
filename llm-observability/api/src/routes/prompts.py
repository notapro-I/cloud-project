from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.entities import LLMRequest
from src.models.schemas import PromptTemplateIn, PromptTemplateOut
from src.services.request_service import create_prompt_template, list_prompt_templates

router = APIRouter(tags=["prompts"])


@router.get("/prompts", response_model=list[PromptTemplateOut])
def get_prompts(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[PromptTemplateOut]:
    return list_prompt_templates(db, limit, offset)


@router.get("/prompts/versions", response_model=list[str])
def get_prompt_versions(db: Session = Depends(get_db)) -> list[str]:
    """Get all distinct prompt versions from requests"""
    stmt = select(
        func.coalesce(
            func.nullif(func.trim(LLMRequest.prompt_version), ""),
            "unversioned"
        ).distinct()
    ).order_by(
        func.coalesce(
            func.nullif(func.trim(LLMRequest.prompt_version), ""),
            "unversioned"
        )
    )
    return db.scalars(stmt).all()


@router.post("/prompt-template", response_model=PromptTemplateOut)
def post_prompt_template(payload: PromptTemplateIn, db: Session = Depends(get_db)) -> PromptTemplateOut:
    return create_prompt_template(db, payload)

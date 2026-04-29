from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.schemas import RequestIngestPayload, RequestOut
from src.services.request_service import ingest_request, list_requests

router = APIRouter(tags=["requests"])


@router.post("/ingest", response_model=RequestOut)
def post_ingest(payload: RequestIngestPayload, db: Session = Depends(get_db)) -> RequestOut:
    return ingest_request(db, payload)


@router.get("/requests", response_model=list[RequestOut])
def get_requests(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    prompt_version: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RequestOut]:
    return list_requests(db, limit, offset, prompt_version=prompt_version)

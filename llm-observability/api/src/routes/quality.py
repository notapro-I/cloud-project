from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.schemas import QualityOut
from src.services.request_service import list_quality_scores

router = APIRouter(tags=["quality"])


@router.get("/quality", response_model=list[QualityOut])
def get_quality(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[QualityOut]:
    return list_quality_scores(db, limit, offset)

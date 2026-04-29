from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.schemas import DriftMetricOut

router = APIRouter(tags=["drift"])


@router.get("/drift", response_model=list[DriftMetricOut])
def get_model_drift(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DriftMetricOut]:
    rows = db.execute(
        text(
            """
            SELECT id,
                   metric_name,
                   model,
                   prompt_template_id,
                   baseline_value,
                   recent_value,
                   delta_pct,
                   detected_at
            FROM drift_metrics
            ORDER BY detected_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    ).mappings()

    return [DriftMetricOut(**row) for row in rows]

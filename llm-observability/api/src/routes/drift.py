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
    prompt_version: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[DriftMetricOut]:
    where_clause = ""
    params: dict[str, int | str] = {"limit": limit, "offset": offset}
    if prompt_version is not None:
        where_clause = "WHERE prompt_version = :prompt_version"
        params["prompt_version"] = prompt_version

    rows = db.execute(
        text(
            f"""
            SELECT id,
                   metric_name,
                   model,
                   prompt_template_id,
                   prompt_version,
                   baseline_value,
                   recent_value,
                   delta_pct,
                   detected_at
            FROM drift_metrics
            {where_clause}
            ORDER BY detected_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings()

    return [DriftMetricOut(**row) for row in rows]

import logging
from typing import Any

from src.config import settings
from src.services.db import get_conn

logger = logging.getLogger(__name__)


def _percent_change(recent: float, baseline: float) -> float | None:
    if baseline == 0:
        return None
    return ((recent - baseline) / baseline) * 100.0


def detect_drift() -> int:
    rows_inserted = 0
    recent_limit = settings.drift_recent_count
    baseline_limit = settings.drift_baseline_count
    baseline_end = recent_limit + baseline_limit

    query = """
        WITH ordered AS (
            SELECT model,
                 COALESCE(NULLIF(TRIM(prompt_version), ''), 'unversioned') AS prompt_version,
                   latency_ms,
                   total_tokens,
                   cost,
                   LENGTH(response) AS response_len,
                   ROW_NUMBER() OVER (
                   PARTITION BY model, COALESCE(NULLIF(TRIM(prompt_version), ''), 'unversioned')
                        ORDER BY created_at DESC
                   ) AS rn
            FROM llm_requests
        ),
        recent AS (
             SELECT model,
                 prompt_version,
                   COUNT(*) AS recent_count,
                   AVG(latency_ms) AS recent_latency,
                   AVG(total_tokens) AS recent_tokens,
                   AVG(cost) AS recent_cost,
                   AVG(response_len) AS recent_response_len
            FROM ordered
            WHERE rn <= %s
             GROUP BY model, prompt_version
        ),
        baseline AS (
             SELECT model,
                 prompt_version,
                   COUNT(*) AS baseline_count,
                   AVG(latency_ms) AS baseline_latency,
                   AVG(total_tokens) AS baseline_tokens,
                   AVG(cost) AS baseline_cost,
                   AVG(response_len) AS baseline_response_len
            FROM ordered
            WHERE rn > %s AND rn <= %s
             GROUP BY model, prompt_version
        )
        SELECT r.model,
             r.prompt_version,
               r.recent_count,
               b.baseline_count,
               r.recent_latency,
               b.baseline_latency,
               r.recent_tokens,
               b.baseline_tokens,
               r.recent_cost,
               b.baseline_cost,
               r.recent_response_len,
               b.baseline_response_len
        FROM recent r
         JOIN baseline b ON b.model = r.model AND b.prompt_version = r.prompt_version
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (recent_limit, recent_limit, baseline_end))
            for row in cur.fetchall():
                (
                    model,
                    prompt_version,
                    recent_count,
                    baseline_count,
                    recent_latency,
                    baseline_latency,
                    recent_tokens,
                    baseline_tokens,
                    recent_cost,
                    baseline_cost,
                    recent_response_len,
                    baseline_response_len,
                ) = row

                if recent_count < settings.drift_min_samples or baseline_count < settings.drift_min_samples:
                    continue

                metrics: dict[str, tuple[float, float]] = {
                    "latency_ms": (float(recent_latency), float(baseline_latency)),
                    "total_tokens": (float(recent_tokens), float(baseline_tokens)),
                    "cost": (float(recent_cost), float(baseline_cost)),
                    "response_length": (float(recent_response_len), float(baseline_response_len)),
                }

                for metric_name, (recent_value, baseline_value) in metrics.items():
                    delta_pct = _percent_change(recent_value, baseline_value)
                    if delta_pct is None:
                        continue
                    if abs(delta_pct) < settings.drift_delta_threshold:
                        continue

                    cur.execute(
                        """
                        INSERT INTO drift_metrics (
                            metric_name,
                            model,
                            prompt_template_id,
                            prompt_version,
                            baseline_value,
                            recent_value,
                            delta_pct
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (metric_name, model, None, prompt_version, baseline_value, recent_value, delta_pct),
                    )
                    rows_inserted += 1

            conn.commit()

    if rows_inserted:
        logger.info("drift_metrics_recorded", extra={"rows": rows_inserted})
    return rows_inserted

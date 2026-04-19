import json
import logging
from typing import Any

import httpx

from src.config import settings
from src.services.db import get_conn

logger = logging.getLogger(__name__)


def _judge_prompt(prompt: str, response: str) -> str:
    return (
        "You are a strict evaluator. Rate the assistant response on correctness, relevance, and completeness. "
        "Return valid JSON only with fields: score (1-5), feedback (short string).\n\n"
        f"Prompt:\n{prompt}\n\nResponse:\n{response}"
    )


def _run_judge_model(prompt: str, response: str) -> tuple[float, str]:
    payload = {
        "model": settings.ollama_judge_model,
        "prompt": _judge_prompt(prompt, response),
        "stream": False,
        "format": "json",
    }
    with httpx.Client(timeout=30.0) as client:
        result = client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
        result.raise_for_status()
    body = result.json()
    raw_text = body.get("response", "{}")
    try:
        parsed = json.loads(raw_text)
        score = float(parsed.get("score", 3.0))
        feedback = str(parsed.get("feedback", "No feedback."))
    except json.JSONDecodeError:
        score = 3.0
        feedback = "Judge output was non-JSON; defaulted score."

    score = min(max(score, 1.0), 5.0)
    return score, feedback


def process_quality_batch(limit: int = 100) -> int:
    processed = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT q.request_id, r.prompt, r.response
                FROM quality_evaluation_queue q
                JOIN llm_requests r ON r.id = q.request_id
                WHERE q.sampled = TRUE AND q.processed = FALSE
                ORDER BY q.created_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

            for request_id, prompt, response in rows:
                try:
                    score, feedback = _run_judge_model(prompt, response)
                    cur.execute(
                        """
                        INSERT INTO quality_scores (request_id, score, feedback)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (request_id) DO UPDATE
                        SET score = EXCLUDED.score,
                            feedback = EXCLUDED.feedback,
                            created_at = NOW()
                        """,
                        (str(request_id), score, feedback),
                    )
                    cur.execute(
                        """
                        UPDATE quality_evaluation_queue
                        SET processed = TRUE
                        WHERE request_id = %s
                        """,
                        (str(request_id),),
                    )
                    processed += 1
                except Exception:
                    logger.exception("quality_scoring_failed", extra={"request_id": str(request_id)})
            conn.commit()

    if processed:
        logger.info("quality_batch_processed", extra={"processed": processed})
    return processed


def run_quality_alert_check() -> int:
    alerts = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH recent AS (
                    SELECT r.prompt_template_id,
                           q.score,
                           ROW_NUMBER() OVER (
                                PARTITION BY r.prompt_template_id
                                ORDER BY q.created_at DESC
                           ) AS rn
                    FROM quality_scores q
                    JOIN llm_requests r ON r.id = q.request_id
                    WHERE r.prompt_template_id IS NOT NULL
                )
                SELECT prompt_template_id, AVG(score) AS avg_score
                FROM recent
                WHERE rn <= %s
                GROUP BY prompt_template_id
                HAVING AVG(score) < %s
                """,
                (settings.quality_window_size, settings.quality_threshold),
            )
            for prompt_template_id, avg_score in cur.fetchall():
                alerts += 1
                logger.warning(
                    "quality_threshold_breach",
                    extra={
                        "prompt_template_id": str(prompt_template_id),
                        "avg_score": float(avg_score),
                        "threshold": settings.quality_threshold,
                    },
                )

    return alerts

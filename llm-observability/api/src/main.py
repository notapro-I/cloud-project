import logging
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.routes.drift import router as drift_router
from src.routes.prompts import router as prompts_router
from src.routes.quality import router as quality_router
from src.routes.requests import router as requests_router
from src.services.metrics_service import reset_daily_cost_if_new_day

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
        }
    },
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {"": {"handlers": ["default"], "level": "INFO"}},
}

dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)
_last_daily_reset = None

app = FastAPI(title="LLM Observability API", version="1.0.0")
app.include_router(requests_router)
app.include_router(quality_router)
app.include_router(prompts_router)
app.include_router(drift_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    global _last_daily_reset
    _last_daily_reset = reset_daily_cost_if_new_day(_last_daily_reset)
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

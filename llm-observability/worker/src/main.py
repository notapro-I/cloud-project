import logging
import time
from logging.config import dictConfig

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import settings
from src.tasks.quality_worker import process_quality_batch, run_quality_alert_check

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


def main() -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_quality_batch, "interval", seconds=settings.worker_poll_seconds, id="quality_scoring")
    scheduler.add_job(run_quality_alert_check, "interval", seconds=settings.worker_poll_seconds, id="quality_alerts")

    scheduler.start()
    logger.info("worker_started", extra={"poll_seconds": settings.worker_poll_seconds})

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        logger.info("worker_stopped")


if __name__ == "__main__":
    main()

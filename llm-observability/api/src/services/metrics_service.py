from datetime import UTC, datetime

from prometheus_client import Counter, Gauge, Histogram

REQUEST_LATENCY_SECONDS = Histogram(
    "request_latency_seconds",
    "LLM request latency in seconds",
    labelnames=("model",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30),
)
TOKEN_USAGE_TOTAL = Counter(
    "token_usage_total",
    "Total number of LLM tokens",
    labelnames=("type", "model"),
)
REQUEST_COUNT = Counter(
    "request_count",
    "Total number of LLM requests",
    labelnames=("model",),
)
DAILY_COST_USD = Gauge("daily_cost_usd", "Estimated total cost for current UTC day")


def record_request_metrics(model: str, latency_ms: float, input_tokens: int, output_tokens: int, cost: float) -> None:
    REQUEST_LATENCY_SECONDS.labels(model=model).observe(latency_ms / 1000.0)
    TOKEN_USAGE_TOTAL.labels(type="input", model=model).inc(input_tokens)
    TOKEN_USAGE_TOTAL.labels(type="output", model=model).inc(output_tokens)
    REQUEST_COUNT.labels(model=model).inc()
    DAILY_COST_USD.inc(cost)


def reset_daily_cost_if_new_day(last_reset_day: datetime | None) -> datetime:
    now = datetime.now(UTC)
    if last_reset_day is None or now.date() != last_reset_day.date():
        DAILY_COST_USD.set(0.0)
        return now
    return last_reset_day

from datetime import UTC, datetime

from prometheus_client import Counter, Gauge, Histogram

REQUEST_LATENCY_SECONDS = Histogram(
    "request_latency_seconds",
    "LLM request latency in seconds",
    labelnames=("model", "prompt_version"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30),
)
TOKEN_USAGE_TOTAL = Counter(
    "token_usage_total",
    "Total number of LLM tokens",
    labelnames=("type", "model", "prompt_version"),
)
REQUEST_COUNT = Counter(
    "request_count",
    "Total number of LLM requests",
    labelnames=("model", "prompt_version"),
)
DAILY_COST_USD = Gauge(
    "daily_cost_usd",
    "Estimated total cost for current UTC day",
    labelnames=("prompt_version",),
)


def _normalize_prompt_version(prompt_version: str | None) -> str:
    value = (prompt_version or "").strip()
    return value if value else "unversioned"


def record_request_metrics(
    model: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    prompt_version: str | None,
) -> None:
    version = _normalize_prompt_version(prompt_version)
    REQUEST_LATENCY_SECONDS.labels(model=model, prompt_version=version).observe(latency_ms / 1000.0)
    TOKEN_USAGE_TOTAL.labels(type="input", model=model, prompt_version=version).inc(input_tokens)
    TOKEN_USAGE_TOTAL.labels(type="output", model=model, prompt_version=version).inc(output_tokens)
    REQUEST_COUNT.labels(model=model, prompt_version=version).inc()
    DAILY_COST_USD.labels(prompt_version=version).inc(cost)


def reset_daily_cost_if_new_day(last_reset_day: datetime | None) -> datetime:
    now = datetime.now(UTC)
    if last_reset_day is None or now.date() != last_reset_day.date():
        DAILY_COST_USD.clear()
        return now
    return last_reset_day

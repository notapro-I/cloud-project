from collections.abc import Awaitable, Callable
from functools import wraps
from time import perf_counter
from typing import Any


def observe_sync(observer: Any, model: str, prompt_template_id: str | None = None) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            prompt = kwargs.get("prompt", "")
            start = perf_counter()
            result = func(*args, **kwargs)
            latency_ms = (perf_counter() - start) * 1000.0
            observer.log_observation_from_result(
                prompt=prompt,
                result=result,
                model=model,
                latency_ms=latency_ms,
                prompt_template_id=prompt_template_id,
            )
            return result

        return wrapped

    return decorator


def observe_async(observer: Any, model: str, prompt_template_id: str | None = None) -> Callable[..., Any]:
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            prompt = kwargs.get("prompt", "")
            start = perf_counter()
            result = await func(*args, **kwargs)
            latency_ms = (perf_counter() - start) * 1000.0
            await observer.alog_observation_from_result(
                prompt=prompt,
                result=result,
                model=model,
                latency_ms=latency_ms,
                prompt_template_id=prompt_template_id,
            )
            return result

        return wrapped

    return decorator

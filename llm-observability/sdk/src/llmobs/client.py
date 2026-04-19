from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

import httpx

from llmobs.config import settings
from llmobs.models import LLMObservation, OpenAIChatResponse


class LLMObserver:
    def __init__(
        self,
        api_base_url: str | None = None,
        openai_base_url: str | None = None,
        openai_api_key: str | None = None,
        ollama_base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_base_url = api_base_url or settings.api_base_url
        self.openai_base_url = openai_base_url or settings.openai_base_url
        self.openai_api_key = openai_api_key or settings.openai_api_key
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        timeout = timeout_seconds or settings.timeout_seconds
        self._logger = logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="llmobs-export")

        self._client = httpx.Client(timeout=timeout)
        self._aclient = httpx.AsyncClient(timeout=timeout)

    def close(self) -> None:
        self._executor.shutdown(wait=False)
        self._client.close()

    async def aclose(self) -> None:
        self._executor.shutdown(wait=False)
        await self._aclient.aclose()

    @staticmethod
    def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
            "gpt-4o": (2.5 / 1_000_000, 10.0 / 1_000_000),
            "default": (0.20 / 1_000_000, 0.80 / 1_000_000),
        }
        in_cost, out_cost = pricing.get(model, pricing["default"])
        return (input_tokens * in_cost) + (output_tokens * out_cost)

    @staticmethod
    def _extract_text(result: Any) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            if "content" in result and isinstance(result["content"], str):
                return result["content"]
            if "response" in result and isinstance(result["response"], str):
                return result["response"]
            choices = result.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
        return str(result)

    @staticmethod
    def _extract_usage(result: Any, prompt: str, response_text: str) -> tuple[int, int, int]:
        if isinstance(result, dict) and isinstance(result.get("usage"), dict):
            usage = result["usage"]
            input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
            return input_tokens, output_tokens, total_tokens

        input_tokens = max(1, len(prompt.split()) * 2 // 3)
        output_tokens = max(1, len(response_text.split()) * 2 // 3)
        return input_tokens, output_tokens, input_tokens + output_tokens

    def _post_observation(self, obs: LLMObservation) -> None:
        try:
            self._client.post(f"{self.api_base_url}/ingest", json=obs.model_dump(mode="json"))
        except Exception:
            self._logger.exception("telemetry_post_failed")

    async def _apost_observation(self, obs: LLMObservation) -> None:
        try:
            await self._aclient.post(f"{self.api_base_url}/ingest", json=obs.model_dump(mode="json"))
        except Exception:
            self._logger.exception("telemetry_post_failed_async")

    def log_observation_from_result(
        self,
        prompt: str,
        result: Any,
        model: str,
        latency_ms: float,
        prompt_template_id: str | None = None,
    ) -> LLMObservation:
        response_text = self._extract_text(result)
        input_tokens, output_tokens, total_tokens = self._extract_usage(result, prompt, response_text)
        cost = self.estimate_cost(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        obs = LLMObservation(
            prompt=prompt,
            response=response_text,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            prompt_template_id=prompt_template_id,
        )
        self._executor.submit(self._post_observation, obs)
        return obs

    async def alog_observation_from_result(
        self,
        prompt: str,
        result: Any,
        model: str,
        latency_ms: float,
        prompt_template_id: str | None = None,
    ) -> LLMObservation:
        response_text = self._extract_text(result)
        input_tokens, output_tokens, total_tokens = self._extract_usage(result, prompt, response_text)
        cost = self.estimate_cost(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        obs = LLMObservation(
            prompt=prompt,
            response=response_text,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            prompt_template_id=prompt_template_id,
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._apost_observation(obs))
        except RuntimeError:
            self._executor.submit(self._post_observation, obs)
        return obs

    def call_openai_chat(self, model: str, prompt: str, prompt_template_id: str | None = None) -> OpenAIChatResponse:
        start = perf_counter()
        headers = {"Content-Type": "application/json"}
        if self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = self._client.post(f"{self.openai_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})
        self.log_observation_from_result(
            prompt=prompt,
            result=raw,
            model=model,
            latency_ms=(perf_counter() - start) * 1000.0,
            prompt_template_id=prompt_template_id,
        )
        return OpenAIChatResponse(content=content, usage=usage, raw=raw)

    def call_ollama(self, model: str, prompt: str, prompt_template_id: str | None = None) -> dict[str, Any]:
        start = perf_counter()
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = self._client.post(f"{self.ollama_base_url}/api/generate", json=payload)
        response.raise_for_status()
        raw = response.json()
        generated = raw.get("response", "")
        usage = {
            "input_tokens": int(raw.get("prompt_eval_count", 0)),
            "output_tokens": int(raw.get("eval_count", 0)),
            "total_tokens": int(raw.get("prompt_eval_count", 0)) + int(raw.get("eval_count", 0)),
        }
        self.log_observation_from_result(
            prompt=prompt,
            result={"response": generated, "usage": usage},
            model=model,
            latency_ms=(perf_counter() - start) * 1000.0,
            prompt_template_id=prompt_template_id,
        )
        return raw

    async def acall_openai_chat(
        self,
        model: str,
        prompt: str,
        prompt_template_id: str | None = None,
    ) -> OpenAIChatResponse:
        start = perf_counter()
        headers = {"Content-Type": "application/json"}
        if self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = await self._aclient.post(
            f"{self.openai_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        raw = response.json()
        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})
        await self.alog_observation_from_result(
            prompt=prompt,
            result=raw,
            model=model,
            latency_ms=(perf_counter() - start) * 1000.0,
            prompt_template_id=prompt_template_id,
        )
        return OpenAIChatResponse(content=content, usage=usage, raw=raw)

    async def acall_ollama(
        self,
        model: str,
        prompt: str,
        prompt_template_id: str | None = None,
    ) -> dict[str, Any]:
        start = perf_counter()
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = await self._aclient.post(f"{self.ollama_base_url}/api/generate", json=payload)
        response.raise_for_status()
        raw = response.json()
        generated = raw.get("response", "")
        usage = {
            "input_tokens": int(raw.get("prompt_eval_count", 0)),
            "output_tokens": int(raw.get("eval_count", 0)),
            "total_tokens": int(raw.get("prompt_eval_count", 0)) + int(raw.get("eval_count", 0)),
        }
        await self.alog_observation_from_result(
            prompt=prompt,
            result={"response": generated, "usage": usage},
            model=model,
            latency_ms=(perf_counter() - start) * 1000.0,
            prompt_template_id=prompt_template_id,
        )
        return raw

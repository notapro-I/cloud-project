from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SDK_SRC_DIR = ROOT_DIR / "sdk" / "src"
if str(SDK_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SDK_SRC_DIR))

from llmobs.client import LLMObserver  # type: ignore[import-not-found]

DEFAULT_VERSIONS = ["v1", "v2", "v3"]
DEFAULT_MODEL = "mistral"

PROMPT_TEMPLATES: dict[str, str] = {
    "v1": "Briefly summarize the following topic in 3 concise bullets (keep under 400 words): {topic}",
    "v2": "Briefly explain the following topic with one practical example (keep under 400 words): {topic}",
    "v3": "Briefly list the key risks and mitigations for the following (keep under 400 words): {topic}",
}

TOPICS = [
    "LLM observability",
    "prompt version tracking",
    "quality scoring",
    "drift detection",
    "latency monitoring",
    "token cost analysis",
    "dashboard filtering",
    "prompt telemetry",
]


def build_prompt(version: str, index: int) -> str:
    template = PROMPT_TEMPLATES.get(version, "Respond briefly about: {topic}")
    topic = TOPICS[index % len(TOPICS)]
    return template.format(topic=f"{topic} run {index + 1}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a batch of synchronous LLM requests while rotating prompt versions."
    )
    parser.add_argument("--count", type=int, default=50, help="Number of requests to send (50-100 is a good range).")
    parser.add_argument(
        "--versions",
        nargs="+",
        default=DEFAULT_VERSIONS,
        help="Prompt versions to cycle through, for example: v1 v2 v3.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name to send to Ollama.")
    parser.add_argument(
        "--api-base-url",
        default="http://localhost:8000",
        help="Observability API base URL.",
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://localhost:11434",
        help="Ollama base URL.",
    )
    parser.add_argument(
        "--delay-ms",
        type=int,
        default=0,
        help="Optional delay between requests in milliseconds.",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Shuffle the version order before sending requests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count < 1:
        raise ValueError("--count must be at least 1")

    versions = [version.strip() for version in args.versions if version.strip()]
    if not versions:
        versions = DEFAULT_VERSIONS.copy()

    if args.shuffle:
        random.shuffle(versions)

    observer = LLMObserver(
        api_base_url=args.api_base_url,
        ollama_base_url=args.ollama_base_url,
    )

    print(f"Sending {args.count} requests using versions: {', '.join(versions)}")
    print(f"Model: {args.model}")

    try:
        for index in range(args.count):
            version = versions[index % len(versions)]
            prompt = build_prompt(version, index)

            response = observer.call_ollama(
                model=args.model,
                prompt=prompt,
                prompt_version=version,
            )
            response_text = response.get("response", "")

            print(
                f"[{index + 1:03d}/{args.count:03d}] version={version} "
                f"prompt_len={len(prompt)} response_len={len(response_text)}"
            )

            if args.delay_ms > 0:
                time.sleep(args.delay_ms / 1000.0)
    finally:
        observer.close()


if __name__ == "__main__":
    main()

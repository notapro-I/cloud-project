# llmobs-sdk

Python SDK for observing LLM prompt/response requests and sending structured telemetry to the LLM observability API.

## Features

- OpenAI-compatible and Ollama call helpers.
- Sync and async wrappers (`observe_sync`, `observe_async`).
- Captures latency, token usage, estimated cost, model metadata, and prompt template linkage.

## Install

```bash
pip install -e .
```

## Usage

```python
from llmobs.client import LLMObserver

observer = LLMObserver(api_base_url="http://localhost:8000")
observer.call_ollama(model="llama3.1", prompt="Explain retrieval augmented generation")
```

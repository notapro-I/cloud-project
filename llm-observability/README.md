# LLM Observability and Prompt Monitoring Platform

A modular observability platform for LLM workloads with Python SDK instrumentation, FastAPI ingestion and query APIs, PostgreSQL persistence, Prometheus metrics, Grafana dashboards, and a background quality scoring worker.

## What is implemented

- Python SDK with sync and async observation wrappers.
- OpenAI-compatible chat call helper and Ollama call helper.
- Request ingestion into PostgreSQL with token/cost/latency metadata.
- Prometheus metrics exposed via `/metrics`.
- API endpoints:
  - `GET /metrics`
  - `GET /requests`
  - `GET /quality`
  - `GET /prompts`
  - `POST /prompt-template`
- Background worker (APScheduler) that:
  - Scores sampled requests using a judge model in Ollama.
  - Writes quality score and feedback to PostgreSQL.
  - Emits threshold-breach alerts via structured logs.
- Docker Compose stack for local development.
- Local Kubernetes manifests for API, PostgreSQL, Prometheus, Grafana, and worker.
- Grafana dashboard JSON export.

## Project structure

- `api/`: FastAPI backend.
- `sdk/`: Instrumentation SDK.
- `worker/`: Quality scorer and alert checker.
- `migrations/`: SQL migration scripts.
- `prometheus/`: Prometheus configuration.
- `grafana/`: Provisioning configuration.
- `dashboards/`: Grafana dashboard JSON exports.
- `k8s/`: Kubernetes manifests.
- `examples/`: SDK usage examples.

## Environment

Use `.env.example` as a template and create `.env` if needed.

## Run locally with Docker Compose

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## API quick checks

Create a prompt template:

```bash
curl -X POST http://localhost:8000/prompt-template \
  -H "Content-Type: application/json" \
  -d '{"name":"summary","version":"v1","template_text":"Summarize: {input}"}'
```

Read requests:

```bash
curl http://localhost:8000/requests
```

Read quality:

```bash
curl http://localhost:8000/quality
```

Read metrics:

```bash
curl http://localhost:8000/metrics
```

## Grafana dashboard import

1. Open Grafana at `http://localhost:3000`.
2. Go to Dashboards -> New -> Import.
3. Upload `dashboards/llm-observability-dashboard.json`.
4. Select datasource `Prometheus` for metric panels.
5. Select datasource `PostgreSQL` for the quality trends panel.

## SDK usage

Install SDK dependencies locally:

```bash
pip install -r sdk/requirements.txt
```

Run the example:

```bash
set PYTHONPATH=sdk/src
python examples/example_usage.py
```

## Notes on design

- Token estimation falls back to lightweight heuristics if provider usage metadata is unavailable.
- Cost uses a simple model pricing map with configurable defaults.
- Sampling for quality scoring is performed at ingestion time and processed asynchronously.
- Alerting currently emits structured logs when average quality for a prompt template drops below threshold.

## Kubernetes local usage

Build images locally first:

```bash
docker build -t llmobs-api:latest api
docker build -t llmobs-worker:latest worker
```

Apply manifests:

```bash
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/prometheus.yaml
kubectl apply -f k8s/grafana.yaml
```

## Next improvements

- Add provider-specific price catalogs and versioning.
- Add robust migration tooling and CI checks.
- Add webhook/email alert dispatchers.
- Add drift detection and prompt diff tracking.

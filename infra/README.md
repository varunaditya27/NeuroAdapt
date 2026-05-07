<div align="center">

# 🏗️ infra
### Docker Compose · Postgres · Prometheus · Multi-service orchestration

*The scaffolding that holds everything together — from your laptop to the cloud.*

[![Docker](https://img.shields.io/badge/Docker-Compose_v2-2496ed)](https://docker.com)
[![Nginx](https://img.shields.io/badge/Nginx-1.25-009639)](https://nginx.org)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-e6522c)](https://prometheus.io)
[![Grafana](https://img.shields.io/badge/Dashboard-Grafana-f46800)](https://grafana.com)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088ff)](https://github.com/features/actions)

> **Primary Owner:** Varun Aditya
> **Supports:** All team members (shared deployment + CI environment)

</div>

---

## 🎯 Responsibility

The `infra/` module owns everything required to **run, monitor, and deploy** NeuroAdapt as a complete system:

- **Docker Compose** orchestration for the backend, frontend, gen-engine, PostgreSQL, and optional quantum jobs
- **Prometheus** scraping for backend/gen-engine metrics
- **Volume-backed Postgres** bootstrap SQL for service schemas
- **Environment examples** for consistent local/bootstrap setup
- **Utility scripts** for config sync, seeding, and health checks

---

## 🗂️ Directory Layout

```
infra/
├── docker-compose.yml          # Full stack orchestrator (base config)
├── docker-compose.dev.yml      # Dev overlay: hot reload mounts
├── docker-compose.prod.yml     # Prod overlay: smaller memory / CPU budgets
├── .env.example                # Local bootstrap env template
## 📊 Monitoring Stack

### Prometheus Scrape Targets

| Metric | Source | Alert Threshold |
|---|---|---|
| `api_request_latency_p50` | Backend `/metrics` | > 200ms |
| `api_request_latency_p99` | Backend `/metrics` | > 1000ms |
| `gen_engine_queue_depth` | Gen Engine `/metrics` | > 10 pending |
| `backend_request_latency_p50` | Backend `/metrics` | > 200ms |

### Prometheus config

Import `monitoring/prometheus.yml` into your monitoring stack or mount it directly in the compose service. It scrapes backend and gen-engine metrics endpoints.

---

## ⚙️ Quantum job

Run the retraining worker with the optional profile:

```bash
docker compose -f infra/docker-compose.yml --profile quantum up quantum
```

The container is intentionally batch-oriented (`restart: "no"`) so a completed retrain does not respawn endlessly.

---

## 🧪 Running the Full Stack Locally

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
docker compose -f infra/docker-compose.yml --profile quantum up quantum
```

## 🌍 Environment Variants

### Production / full stack (`docker-compose.yml`)

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

Full stack with:
- Persistent PostgreSQL volume
- In-process backend state cache with Postgres replay persistence
- Gen-engine + Kokoro TTS for generation flows
- Optional quantum retraining job via `--profile quantum`

---

### Development (`docker-compose.dev.yml`)

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
```

Overrides for local development:
- **Hot reload** on frontend (Next.js dev server) and backend/gen-engine (uvicorn --reload)
- **Verbose logging** on all services
- **Bind mounts** for source edits during development
- **Port 5432 exposed** for direct Postgres access via psql or a GUI client

---

### Production overlays (`docker-compose.prod.yml`)

```bash
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d
```

Optimised for resource-constrained environments:
- Smaller memory/CPU budgets on stateless services
- No bind mounts
- Keeps the same networking and service naming as the base stack

---

## 📊 Monitoring Stack

### Prometheus Scrape Targets

| Metric | Source | Alert Threshold |
|---|---|---|
| `api_request_latency_p50` | Backend `/metrics` | > 200ms |
| `api_request_latency_p99` | Backend `/metrics` | > 1000ms |
| `gen_engine_queue_depth` | Gen Engine `/metrics` | > 10 pending |
| `backend_request_latency_p50` | Backend `/metrics` | > 200ms |

### Prometheus config

Import `monitoring/prometheus.yml` into your monitoring stack or mount it directly in the compose service. It scrapes backend and gen-engine metrics endpoints.

---

## ⚙️ Quantum job

Run the retraining worker with the optional profile:

```bash
docker compose -f infra/docker-compose.yml --profile quantum up quantum
```

The container is intentionally batch-oriented (`restart: "no"`) so a completed retrain does not respawn endlessly.

---

## 🧪 Running the Full Stack Locally

```bash
docker compose -f infra/docker-compose.yml up --build -d
docker compose -f infra/docker-compose.yml -f infra/docker-compose.dev.yml up
docker compose -f infra/docker-compose.yml --profile quantum up quantum
```

---

<div align="center">

*Part of the [NeuroAdapt](../README.md) monorepo*
**🏗️ One command to launch. One dashboard to watch. Zero surprises in production.**

</div>

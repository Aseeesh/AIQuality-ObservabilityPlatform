# AI Quality & Observability Platform

End-to-end **quality, evaluation, tracing, SLO, and incident-response** platform for
LLM/AI systems. Brings production-grade observability (OpenTelemetry traces, metrics,
anomaly detection) together with automated LLM-as-judge evaluation, SLO/error-budget
enforcement, automated root-cause analysis, and MCP-driven agentic automation.

## Architecture

| Layer | Tech | Responsibility |
|-------|------|----------------|
| `backend/` | C# .NET 9 (API / Core / Infrastructure / Tests) | Tracing, evaluation orchestration, SLO engine, incidents, feedback APIs |
| `python-services/` | Python 3.12 (FastAPI) | LLM-judge evaluation, anomaly detection, automated RCA, feedback processing, MCP integration |
| `frontend/` | React 19.2 + Vite + Tailwind | Dashboards for tracing, evaluation, monitoring, SLO, incidents, feedback |
| `infrastructure/` | Terraform | Cloud infra modules |
| `config/` | YAML | Quality gates, evaluation rubrics, SLO defs, Prometheus/Grafana, alerts |
| `docker/` | Compose | Local dev / base / prod stacks |

## Quick start

```bash
make up          # start the dev stack
make build       # build backend + frontend
make eval        # run an evaluation pass
```

See `docs/` for architecture, API, quality, monitoring, and operations guides.

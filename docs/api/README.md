# API Reference

Base URLs (local dev): **.NET API** `http://localhost:5099` · **Python services** on their own
ports (anomaly-detector/automated-rca/feedback-processor expose FastAPI apps). All bodies are
JSON. Enums serialize as integers (noted per type).

> Every `.../demo` endpoint seeds realistic data so the dashboard and these docs are explorable
> without a live workload.

---

## Tracing API (.NET)

Coarse trace records:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/tracing` | List trace records (most recent first) |
| `GET` | `/api/tracing/{id}` | Get one trace record |
| `POST` | `/api/tracing` | Start a trace `{name, model}` |
| `POST` | `/api/tracing/{id}/complete` | Complete `{durationMs, qualityScore}` |

Span-level (OpenTelemetry) tracing:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/spans/traces?limit=` | Trace summaries (explorer) |
| `GET` | `/api/spans/traces/{traceId}` | Full span tree (waterfall) |
| `POST` | `/api/spans/query` | Filter spans `{traceId?, operation?, minDurationMs?, status?, aiKind?, limit?}` |
| `GET` | `/api/spans/profile` | Per-operation p50/p95/p99 + slowest traces |
| `GET` | `/api/spans/traces/{traceId}/rca` | Per-trace root-cause analysis |
| `POST` | `/api/spans/demo` | Seed a healthy + a failing trace |

`SpanStatus`: `0` Unset · `1` Ok · `2` Error. Each span carries an optional `aiContext`
(`llm_call` / `quality_check` / `retrieval` / `routing` / `mcp_tool_call`).

---

## Evaluation API (.NET)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/evaluation/batch` | Run a batch `{dataset, environment, rubricSet, items:[{prompt,output,context,references}]}` → `BatchEvaluationResult` (run + perRubric + gates + regression) |
| `POST` | `/api/evaluation/ci-gate` | Same as batch; **HTTP 422** when a gate fails (CI pass/fail) |
| `GET` | `/api/evaluation/runs?dataset=` | Run history |
| `GET` | `/api/evaluation/runs/{id}/report` | Report + executive summary |
| `POST` | `/api/evaluation/demo` | Seed a baseline + a regressed run |

Gate status / SLI status enums: `0` Passed/Healthy · `1` Warning/AtRisk · `2` Failed/Breached.

---

## Improvement API (.NET)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/improvement/plan` | `{dataset, environment, targetQuality?, userSatisfaction?}` → prioritised opportunities + A/B/canary experiment |
| `POST` | `/api/improvement/analyze` | Quality analysis only (trend/gaps/cost/latency) |
| `POST` | `/api/improvement/demo` | Seed a weak run and return a plan |

---

## SLO API (.NET)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/slo` | Compliance snapshot across all SLOs |
| `GET` | `/api/slo/definitions` | List SLO definitions |
| `POST` | `/api/slo/definitions` | Register an `SLODefinition` |
| `GET` | `/api/slo/{name}` | Compliance for one SLO |
| `POST` | `/api/slo/{name}/observe?value=` | Record a raw observation (good/bad via the definition) |
| `GET` | `/api/slo/report` | Compliance report + executive summary |
| `POST` | `/api/slo/demo` | Seed SLI data (one breaching its budget) |

`SLOMetricType`: `0` Latency · `1` Accuracy · `2` Availability · `3` Quality · `4` Business.

---

## Incident API (.NET)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/incidents` | Create `IncidentRequest` → classify, assign, notify, **auto-RCA** if `traceId` set |
| `GET` | `/api/incidents` | Active incidents |
| `GET` | `/api/incidents/{id}` | Full `IncidentView` (notifications + timeline + RCA) |
| `POST` | `/api/incidents/{id}/acknowledge` | `{responder}` |
| `POST` | `/api/incidents/{id}/escalate` | `{to}` — bumps severity |
| `POST` | `/api/incidents/{id}/resolve` | `{resolution}` |
| `GET` | `/api/incidents/{id}/postmortem` | Timeline + root cause + action items |
| `POST` | `/api/incidents/demo` | Seed a failing trace and open a linked incident |

`IncidentSeverity`: `0` Sev1 … `3` Sev4. `IncidentStatus`: `0` Open · `1` Acknowledged · `2` Escalated · `3` Resolved.

---

## Monitoring API (Python · anomaly-detector)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health |
| `POST` | `/monitor` | `{name, value, dimensions?, labels?}` → anomalies + alerts + SLO + investigation + self-healing |
| `GET` | `/slo` | SLO/error-budget compliance snapshot |

## Feedback API (Python · feedback-processor)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/feedback` | `{prompt, response, rating?, thumbs?, text?}` → sentiment + topics + insights + eval case |
| `GET` | `/insights` | Aggregated sentiment/topics/trend |
| `GET` | `/eval-dataset` | Content-versioned eval dataset (JSONL) |

## RCA API (Python · automated-rca)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/analyze` | `{title, traces?, logs?, metrics?, signals?}` → ranked hypotheses + recommendations + narrative |

## MCP tools

Not HTTP — invoked over the MCP protocol (or in-process). See
[MCP integration](../architecture/mcp-integration.md) for the 12 tools and their schemas.

# Tests

Two layers of automated tests:

| Layer | Location | Runner |
| --- | --- | --- |
| **Per-service unit suites** | `python-services/*/tests/`, `backend/AIQuality.Tests/` | `scripts/run-python-tests.sh`, `dotnet test backend/AIQuality.sln` |
| **Cross-cutting framework** | `tests/` (this dir) | `./tests/run-tests.sh` |

## Cross-cutting framework (`tests/`)

Exercises the **real** Python services in-process (no mocks for the service logic itself), so
the suites validate genuine cross-service behaviour. Stdlib-only — no install needed.

```
tests/
├── framework/            # shared harness, data factories, mock services, path wiring
│   ├── factories.py      #   EvalItem/Trace/MetricSeries/Feedback/IncidentEvidence factories
│   ├── mocks.py          #   CannedJudge, MockNotificationSink, FakeApiClient
│   └── harness.py        #   Suite runner + `timed()` latency helper
├── quality-validation/   # judge calibration, rubric validation, SLO tracking, quality gates
├── integration/          # MCP tool registration, agent interaction, automation execution
├── performance/          # evaluation throughput, monitoring scalability, tracing, tool latency
└── e2e/                  # the full quality loop (feedback → eval → gate → incident → improve)
```

Run everything:

```bash
./tests/run-tests.sh        # framework suites
./scripts/run-python-tests.sh   # per-service unit suites
dotnet test backend/AIQuality.sln
```

## Performance budgets (asserted in `performance/`)

These mirror the platform's success metrics; the offline backends run far inside them:

| Check | Budget | Typical |
| --- | --- | --- |
| Evaluation latency | < 3000 ms/req | ~0.15 ms |
| Anomaly detection | < 1000 ms | ~0.07 ms |
| MCP tool execution | < 100 ms | < 0.1 ms |

## CI

`quality-ci` runs all three layers on every push/PR (backend, python unit + framework, frontend).

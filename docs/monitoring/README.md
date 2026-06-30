# Monitoring

## Stack

| Concern | Tool | Where |
| --- | --- | --- |
| Distributed traces | Jaeger (OTLP) | http://localhost:16686 |
| Metrics | Prometheus | `config/monitoring/prometheus.yml` |
| Dashboards | Grafana | `config/monitoring/grafana-dashboards/` |
| Quality anomalies | anomaly-detector (`QualityMonitor`) | `python-services/anomaly-detector` |
| In-app dashboard | React Monitoring page | live WS feed + Recharts |

## Anomaly detection

`QualityMonitor.monitor(metric)` runs an **ensemble** and fuses the verdicts:

| Detector | Catches |
| --- | --- |
| Z-score | point outliers (normal-ish data) |
| IQR (Tukey) | outliers in heavy-tailed / non-normal data |
| EWMA residual | level shifts / trends a global z-score misses |
| Isolation Forest (MAD-gated) | multivariate outliers (sklearn; robust fallback) |
| Multi-dimensional | correlated multi-signal anomalies (L2 of per-dim deviations) |

Severity (P1–P4) rises with detector **consensus** and deviation magnitude. The detector stays
quiet below `min_samples`, and the Isolation Forest is gated behind a robust MAD/σ magnitude
check so it doesn't fire on a low-variance baseline.

Tuning lives in `MonitorConfig` (`window_size`, `min_samples`, `zscore_threshold`, `iqr_k`,
`ewma_alpha`, `seasonal_period`).

## Alert routing & escalation

`AlertManager` maps the worst anomaly severity to an `EscalationPolicy`:

| Severity | Routes |
| --- | --- |
| P1 | PagerDuty (primary) · Slack #incidents · Email sre-leads |
| P2 | PagerDuty (primary) · Slack #incidents |
| P3 | Slack #quality-alerts |
| P4 | Slack #quality-noise |

A cooldown de-dupes sustained anomalies; an optional on-call callback models PagerDuty/Opsgenie.

## SLO / error-budget monitoring

`SLOTracker` computes SLIs over rolling event windows and reports **error-budget consumed /
remaining / burn rate**. The monitoring dashboard surfaces compliance and budget bars; fast
burns page, slow burns ticket (see the [Quality guide](../quality/README.md#slo-definition)).

## Self-healing suggestions

On an anomaly the monitoring agent classifies the signal and proposes remediations
(`quality_degradation` → roll back prompt/model; `performance_degradation` → scale out / shorten
prompts; `drift` → refresh calibration). These feed the incident-response automation.

## Dashboard

The React **Monitoring** page subscribes to a live feed (`useLiveFeed`; WebSocket with a
simulated fallback) and renders per-metric line charts with anomaly markers plus a rolling alert
feed. Point `VITE_WS_URL` at a real metric stream to go live.

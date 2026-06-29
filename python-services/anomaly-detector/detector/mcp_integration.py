"""MCP integration: AI-agent-driven monitoring.

Exposes monitoring capabilities as MCP tools and provides a lightweight "monitoring agent"
that, on an anomaly, runs an automated investigation (correlate signals, classify) and
proposes self-healing actions. The logic is local/deterministic so it runs without an LLM;
an MCP server (python-services/mcp-integration) can register these tools for an LLM agent to
call, and the investigation summary can seed an LLM prompt for richer narratives.
"""
from __future__ import annotations

from .config import Anomaly, MonitoringResult, QualityMetric, Severity
from .patterns import linear_trend


class MCPIntegration:
    def __init__(self, metric_history: dict[str, list[float]] | None = None):
        # A reference to the collector's series, used for cross-signal correlation.
        self._history_provider = metric_history if metric_history is not None else {}

    # ------------------------------------------------------------- automated investigation
    def investigate(self, metric: QualityMetric, anomalies: list[Anomaly],
                    history: list[float]) -> dict:
        """Automated first-pass investigation an on-call would otherwise do by hand."""
        direction, slope = linear_trend(history)
        worst = min(anomalies, key=lambda a: a.severity)
        return {
            "summary": f"{metric.name} anomaly ({worst.severity.label}) — value {metric.value:.3f}, "
                       f"{worst.direction} vs baseline; series trend is {direction}.",
            "detectors_agreeing": sorted({a.method for a in anomalies}),
            "trend": direction,
            "slope_per_step": round(slope, 5),
            "classification": self._classify(metric, anomalies, direction),
            "correlated_metrics": self._correlated(metric.name),
        }

    def _classify(self, metric: QualityMetric, anomalies: list[Anomaly], trend: str) -> str:
        worst = min(anomalies, key=lambda a: a.severity)
        if worst.direction == "low" and "quality" in metric.name.lower():
            return "quality_degradation"
        if worst.direction == "high" and ("latency" in metric.name.lower() or "error" in metric.name.lower()):
            return "performance_degradation"
        if trend in ("increasing", "decreasing"):
            return "drift"
        return "spike"

    def _correlated(self, metric_name: str) -> list[str]:
        """Other metrics currently trending the same way — candidate co-causes."""
        out = []
        for name, series in self._history_provider.items():
            if name == metric_name or len(series) < 3:
                continue
            if linear_trend(series)[0] in ("increasing", "decreasing"):
                out.append(name)
        return out

    # ------------------------------------------------------------- self-healing suggestions
    def self_healing_suggestions(self, metric: QualityMetric, anomalies: list[Anomaly]) -> list[str]:
        """Concrete, actionable remediations keyed off the anomaly classification."""
        cls = self._classify(metric, anomalies, linear_trend(self._history_provider.get(metric.name, []))[0])
        catalog = {
            "quality_degradation": [
                "Roll back to the last known-good prompt/model version.",
                "Route traffic to a higher-capability model for affected requests.",
                "Trigger a batch re-evaluation to confirm and scope the regression.",
            ],
            "performance_degradation": [
                "Scale out the inference pool / increase concurrency limits.",
                "Enable response streaming and shorten prompts to cut latency.",
                "Shed load by deferring low-priority evaluation jobs.",
            ],
            "drift": [
                "Refresh calibration/baseline against a recent labelled set.",
                "Inspect upstream data sources for distribution shift.",
            ],
            "spike": [
                "Verify the data point isn't a telemetry/ingestion glitch.",
                "Check for a correlated deploy or config change at this timestamp.",
            ],
        }
        return catalog.get(cls, ["Open an incident and gather more context."])

    # ------------------------------------------------------------- MCP tool specs
    def tools(self, monitor) -> list[dict]:
        """MCP tool specs an agent can call against a live QualityMonitor."""
        return [
            {
                "name": "check_metric",
                "description": "Submit a metric value and get anomaly/alert/SLO results.",
                "input_schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "value": {"type": "number"}},
                    "required": ["name", "value"],
                },
                "handler": lambda name, value: monitor.monitor_sync(QualityMetric(name, value)).as_dict(),
            },
            {
                "name": "slo_status",
                "description": "Return the SLO/error-budget compliance snapshot.",
                "input_schema": {"type": "object", "properties": {}},
                "handler": lambda: monitor.slo.compliance_report(),
            },
        ]

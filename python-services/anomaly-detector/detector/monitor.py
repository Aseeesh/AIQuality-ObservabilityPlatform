"""QualityMonitor: real-time quality monitoring with AI agents.

Ties the pieces together: collect a metric, detect anomalies (statistical + ML + multi-dim),
raise alerts with escalation, update SLO/error-budget, and — on an anomaly — run an automated
MCP-agent investigation and propose self-healing actions.
"""
from __future__ import annotations

import asyncio

from .alerts import AlertManager
from .algorithms import AnomalyDetector
from .config import MonitorConfig, MonitoringResult, QualityMetric
from .mcp_integration import MCPIntegration
from .metrics import MetricCollector
from .slo import SLOTracker


class QualityMonitor:
    """Real-time quality monitoring with AI agents."""

    def __init__(self, config: MonitorConfig | None = None,
                 alerts: AlertManager | None = None,
                 slo: SLOTracker | None = None):
        self.config = config or MonitorConfig()
        self.metrics = MetricCollector(self.config.window_size)
        self.detector = AnomalyDetector(self.config)
        self.alerts = alerts or AlertManager()
        self.slo = slo or SLOTracker()
        # The MCP agent reads the collector's series for cross-signal correlation.
        self.mcp = MCPIntegration(metric_history=self.metrics._series)  # type: ignore[attr-defined]

    async def monitor(self, metric: QualityMetric) -> MonitoringResult:
        """Monitor a quality metric in real-time and return the full result."""
        # 1. Collect (history is the series *before* this value, for unbiased detection).
        history = self.metrics.record(metric)

        # 2. Detect anomalies.
        anomalies = self.detector.detect(metric, history)

        # 3. Alert + escalate.
        alerts = self.alerts.evaluate(metric.name, anomalies)

        # 4. SLO / error budget.
        sli = self.slo.record(metric.name, metric.value) if self.slo.has(metric.name) else None
        budget = self.slo.error_budget(metric.name) if self.slo.has(metric.name) else None

        result = MonitoringResult(
            metric=metric.name, value=metric.value,
            is_anomaly=bool(anomalies), anomalies=anomalies, alerts=alerts,
            sli=sli, error_budget=budget,
        )

        # 5. On anomaly: automated investigation + self-healing suggestions (MCP agent).
        if anomalies:
            result.investigation = self.mcp.investigate(metric, anomalies, history)
            result.healing_suggestions = self.mcp.self_healing_suggestions(metric, anomalies)

        return result

    def monitor_sync(self, metric: QualityMetric) -> MonitoringResult:
        return asyncio.run(self.monitor(metric))

    def mcp_tools(self) -> list[dict]:
        return self.mcp.tools(self)

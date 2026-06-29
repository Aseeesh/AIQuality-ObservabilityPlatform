"""Monitoring Agent: proactive monitoring.

Detects anomalies on an incoming metric and checks SLO compliance; if it finds an anomaly,
it returns a "raise_incident" action the incident automation can act on.
"""
from __future__ import annotations

from ..config import AgentResult
from ..registry import ToolRegistry


class MonitoringAgent:
    name = "monitoring-agent"

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def run(self, name: str, value: float, history: list[float]) -> AgentResult:
        anomaly = self.registry.call("detect_anomaly", name=name, value=value, history=history)
        slo = self.registry.call("check_slo", name=name, value=value)

        actions = []
        if anomaly["is_anomaly"]:
            actions.append("raise_incident")
            actions.append("notify_on_call")
        summary = f"{name}={value} anomaly={anomaly['is_anomaly']}"
        return AgentResult(self.name, summary, actions, {"anomaly": anomaly, "slo": slo})

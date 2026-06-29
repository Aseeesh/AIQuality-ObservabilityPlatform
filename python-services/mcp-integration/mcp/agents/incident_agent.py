"""Incident Agent: automated incident response.

Creates an incident, runs automated RCA from the supplied evidence, and escalates when the
analysis is high-confidence — the closed loop from a monitoring signal to a triaged incident
with a root cause attached.
"""
from __future__ import annotations

from ..config import AgentResult
from ..registry import ToolRegistry


class IncidentAgent:
    name = "incident-agent"

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def run(self, title: str, severity: str = "P2", signals: dict | None = None,
            traces: list[dict] | None = None, logs: list[dict] | None = None,
            metrics: list[dict] | None = None) -> AgentResult:
        incident = self.registry.call("create_incident", title=title, severity=severity,
                                      signals=signals or {})
        rca = self.registry.call("postmortem_analyze", incident_id=incident["id"],
                                 traces=traces or [], logs=logs or [], metrics=metrics or [])

        actions = ["create_incident", "postmortem_analyze"]
        # Escalate severe, confident incidents automatically.
        if severity in ("P1", "P2") and rca.get("confidence", 0) >= 0.6:
            self.registry.call("escalate_incident", incident_id=incident["id"], to="incident-commander")
            actions.append("escalate_incident")
        summary = f"{incident['id']} root_cause={rca.get('root_cause')} confidence={rca.get('confidence')}"
        return AgentResult(self.name, summary, actions, {"incident": incident, "rca": rca})

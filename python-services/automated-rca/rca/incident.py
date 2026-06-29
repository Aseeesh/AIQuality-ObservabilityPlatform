"""Incident management: creation, severity classification, escalation, post-incident review."""
from __future__ import annotations

import uuid

from .config import Incident, RCAReport, Severity, SpanRecord


class IncidentManager:
    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def create(self, title: str, *, description: str = "", trace_id: str | None = None,
               signals: dict[str, str] | None = None,
               traces: list[SpanRecord] | None = None,
               logs: list | None = None, metrics: list | None = None) -> Incident:
        incident = Incident(
            id=f"INC-{uuid.uuid4().hex[:8]}",
            title=title, description=description, trace_id=trace_id,
            signals=signals or {}, traces=traces or [], logs=logs or [], metrics=metrics or [],
        )
        incident.severity = self.classify_severity(incident)
        self._incidents[incident.id] = incident
        return incident

    def classify_severity(self, incident: Incident) -> Severity:
        """Severity from blast radius: error-span count, critical logs, and metric deviation."""
        error_spans = sum(1 for s in incident.traces if s.status == "error")
        critical_logs = sum(1 for l in incident.logs if l.level == "CRITICAL")
        max_dev = max((abs(m.deviation) for m in incident.metrics), default=0.0)

        if critical_logs or error_spans >= 3 or max_dev >= 1.0:
            return Severity.P1
        if error_spans >= 1 or max_dev >= 0.5:
            return Severity.P2
        if max_dev >= 0.25:
            return Severity.P3
        return Severity.P4

    def escalation_path(self, severity: Severity) -> list[str]:
        return {
            Severity.P1: ["pagerduty:incident-commander", "slack:#incidents", "statuspage:update"],
            Severity.P2: ["pagerduty:on-call", "slack:#incidents"],
            Severity.P3: ["slack:#ops"],
            Severity.P4: ["slack:#ops-noise"],
        }.get(severity, ["slack:#ops"])

    def post_incident_review(self, incident: Incident, report: RCAReport) -> dict:
        """Generate a post-incident review skeleton from the incident + RCA report."""
        return {
            "incident_id": incident.id,
            "title": incident.title,
            "severity": incident.severity.label,
            "root_cause": report.root_cause,
            "what_happened": report.narrative,
            "action_items": [r.action for r in report.recommendations],
            "follow_ups": [
                "Add a regression test / monitor for this failure mode.",
                "Review whether alerting fired promptly and routed correctly.",
            ],
        }

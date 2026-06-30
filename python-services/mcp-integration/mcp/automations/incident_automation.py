"""Incident-response automation plan.

On an `anomaly_detected` event: create + triage an incident (incident agent runs RCA and
auto-escalates severe, confident cases), then attach a self-healing recommendation derived
from the root cause. The closed loop from signal to triaged, root-caused incident.
"""
from __future__ import annotations

from .config import Trigger


def build_incident_plan(auto, trigger: Trigger) -> list:
    p = trigger.payload

    def triage(ctx: dict) -> dict:
        result = auto.server.agents.incident.run(
            title=p.get("title", "Anomaly detected"),
            severity=p.get("severity", "P2"),
            signals=p.get("signals", {}),
            traces=p.get("traces", []), logs=p.get("logs", []), metrics=p.get("metrics", []))
        ctx["incident"] = result.as_dict()
        return ctx["incident"]

    def recommend(ctx: dict) -> dict:
        rca = ctx.get("incident", {}).get("data", {}).get("rca", {})
        category = rca.get("category", "unknown")
        playbook = {
            "dependency_failure": "Apply timeout+retry+circuit-breaker around the failing dependency.",
            "performance": "Scale out / optimise the bottleneck operation.",
            "quality_regression": "Roll back the model/prompt; re-run quality gates.",
            "change_induced": "Roll back the correlated change.",
        }
        return {"recommendation": playbook.get(category, "Investigate further; gather more telemetry.")}

    return [("triage_incident", triage), ("recommend_remediation", recommend)]

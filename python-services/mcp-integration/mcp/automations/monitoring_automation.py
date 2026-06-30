"""Monitoring automation plan.

On an incoming metric: run anomaly detection + SLO check (monitoring agent); if anomalous,
trigger automated investigation/incident response and emit self-healing suggestions. This is
the "see a problem, act on it" loop, fully tool-driven.
"""
from __future__ import annotations

from .config import Trigger


def build_monitoring_plan(auto, trigger: Trigger) -> list:
    p = trigger.payload
    name, value = p.get("name", "metric"), p.get("value", 0.0)
    history = p.get("history", [])

    def detect(ctx: dict) -> dict:
        ctx["mon"] = auto.server.agents.monitoring.run(name=name, value=value, history=history).as_dict()
        ctx["anomaly"] = ctx["mon"]["data"]["anomaly"]["is_anomaly"]
        return ctx["mon"]

    def investigate(ctx: dict) -> dict:
        if not ctx.get("anomaly"):
            return {"skipped": True, "reason": "no anomaly"}
        # Hand off to the incident agent for create + RCA (+ escalate if severe).
        result = auto.server.agents.incident.run(
            title=f"Anomaly on {name}", severity=p.get("severity", "P2"),
            signals={"metric": name}, metrics=[{"name": name, "value": value, "baseline": p.get("baseline")}])
        ctx["incident"] = result.as_dict()
        return ctx["incident"]

    def self_heal(ctx: dict) -> dict:
        if not (ctx.get("anomaly") and auto.config.self_heal):
            return {"skipped": True}
        return {"suggestions": [
            "Route affected traffic to a fallback model.",
            "Scale out inference capacity.",
            "Re-run calibration if the signal is a quality metric.",
        ]}

    return [("detect_anomaly", detect), ("investigate", investigate), ("self_heal", self_heal)]

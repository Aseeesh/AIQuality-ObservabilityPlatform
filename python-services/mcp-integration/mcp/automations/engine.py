"""AutomationEngine: register automations and fire them on triggers.

An automation binds a trigger (an event name like "anomaly_detected" or a schedule like
"nightly") to a handler that orchestrates agents/tools. This is the layer that turns the
agents into a hands-off quality-improvement pipeline: a monitoring anomaly fires the incident
automation; a nightly trigger fires the benchmark/improvement automation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..config import AutomationResult


@dataclass
class Automation:
    name: str
    trigger: str                          # event name or schedule label
    handler: Callable[[dict], list[dict]]  # receives the event payload, returns step results


class AutomationEngine:
    def __init__(self) -> None:
        self._automations: list[Automation] = []

    def register(self, automation: Automation) -> None:
        self._automations.append(automation)

    def list(self) -> list[dict]:
        return [{"name": a.name, "trigger": a.trigger} for a in self._automations]

    def fire(self, trigger: str, payload: dict | None = None) -> list[AutomationResult]:
        """Run every automation bound to `trigger`."""
        payload = payload or {}
        out: list[AutomationResult] = []
        for a in self._automations:
            if a.trigger != trigger:
                continue
            try:
                results = a.handler(payload)
                out.append(AutomationResult(a.name, triggered=True, results=results))
            except Exception as e:  # an automation failure must not break the trigger
                out.append(AutomationResult(a.name, triggered=True, results=[{"error": str(e)}]))
        return out

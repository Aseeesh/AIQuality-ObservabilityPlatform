"""Alerting and escalation.

Turns anomalies into alerts via configurable rules, assigns severity (P1-P4), applies an
escalation policy (which channels/teams to notify), and de-duplicates with a cooldown so a
sustained anomaly doesn't spam. An optional on-call callback models PagerDuty/Opsgenie.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from .config import Alert, Anomaly, Severity


@dataclass
class EscalationPolicy:
    """Per-severity notification routing. Faster, wider escalation for severe alerts."""
    routes: dict[Severity, list[str]] = field(default_factory=lambda: {
        Severity.P1: ["pagerduty:on-call-primary", "slack:#incidents", "email:sre-leads"],
        Severity.P2: ["pagerduty:on-call-primary", "slack:#incidents"],
        Severity.P3: ["slack:#quality-alerts"],
        Severity.P4: ["slack:#quality-noise"],
    })

    def route(self, severity: Severity) -> list[str]:
        return self.routes.get(severity, ["slack:#quality-alerts"])


@dataclass
class AlertRule:
    """Fires when a metric has an anomaly meeting (or exceeding) min_severity, optionally only
    in a given direction, after `for_consecutive` consecutive breaches."""
    name: str
    metric: str | None = None         # None = applies to any metric
    min_severity: Severity = Severity.P3
    direction: str | None = None      # "high" | "low" | None (any)
    for_consecutive: int = 1


class AlertManager:
    def __init__(self, rules: list[AlertRule] | None = None,
                 policy: EscalationPolicy | None = None,
                 on_call: Callable[[Alert], None] | None = None,
                 cooldown_seconds: float = 60.0):
        self.rules = rules or self._default_rules()
        self.policy = policy or EscalationPolicy()
        self.on_call = on_call
        self.cooldown = cooldown_seconds
        self._breach_streak: dict[str, int] = {}
        self._last_fired: dict[str, float] = {}

    @staticmethod
    def _default_rules() -> list[AlertRule]:
        return [
            AlertRule("critical-quality-drop", min_severity=Severity.P1),
            AlertRule("quality-degradation", min_severity=Severity.P3),
        ]

    def evaluate(self, metric_name: str, anomalies: list[Anomaly]) -> list[Alert]:
        """Match anomalies against rules and emit alerts (deduped, escalated)."""
        if not anomalies:
            self._breach_streak.pop(metric_name, None)
            return []

        worst = min(anomalies, key=lambda a: a.severity)  # P1 < P4 numerically => most severe
        streak = self._breach_streak.get(metric_name, 0) + 1
        self._breach_streak[metric_name] = streak

        alerts: list[Alert] = []
        for rule in self.rules:
            if rule.metric and rule.metric != metric_name:
                continue
            if worst.severity > rule.min_severity:  # not severe enough
                continue
            if rule.direction and not any(a.direction == rule.direction for a in anomalies):
                continue
            if streak < rule.for_consecutive:
                continue
            if not self._cooldown_ok(rule.name, metric_name):
                continue

            alert = Alert(
                rule=rule.name, severity=worst.severity, metric=metric_name,
                message=f"{metric_name}: {worst.message} (via {worst.method})",
                escalation=self.policy.route(worst.severity),
            )
            alerts.append(alert)
            if self.on_call:
                self.on_call(alert)
        return alerts

    def _cooldown_ok(self, rule: str, metric: str) -> bool:
        key = f"{rule}:{metric}"
        now = time.time()
        if now - self._last_fired.get(key, 0) < self.cooldown:
            return False
        self._last_fired[key] = now
        return True

"""SLO/SLI tracking and error-budget accounting.

An SLO pairs a Service-Level Indicator (SLI) — the fraction of events that are "good" — with
an objective (the target fraction). The error budget is the allowed unreliability (1 -
objective); as bad events accumulate the budget burns down. Burn rate normalises consumption
by how much of the window has elapsed, so fast burns page early.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable

from .config import ErrorBudget, SLIResult


@dataclass
class SLO:
    name: str
    objective: float                       # e.g. 0.99 => 99% of events must be good
    window: int = 200                      # number of recent events the SLI is measured over
    # Predicate deciding whether one metric value counts as a "good" event.
    is_good: Callable[[float], bool] = field(default=lambda v: True)


class SLOTracker:
    def __init__(self, slos: list[SLO] | None = None):
        self._slos = {s.name: s for s in (slos or self._defaults())}
        self._events: dict[str, deque[bool]] = {name: deque(maxlen=s.window) for name, s in self._slos.items()}

    @staticmethod
    def _defaults() -> list[SLO]:
        return [
            # Quality SLO: a score >= 0.8 is a "good" response.
            SLO("quality-score", objective=0.95, is_good=lambda v: v >= 0.8),
            # Latency SLO: under 2000 ms is "good".
            SLO("latency-ms", objective=0.99, is_good=lambda v: v <= 2000),
        ]

    def has(self, metric_name: str) -> bool:
        return metric_name in self._slos

    def record(self, metric_name: str, value: float) -> SLIResult | None:
        slo = self._slos.get(metric_name)
        if slo is None:
            return None
        events = self._events[metric_name]
        events.append(slo.is_good(value))
        measured = sum(events) / len(events)
        return SLIResult(name=metric_name, value=measured, objective=slo.objective, met=measured >= slo.objective)

    def error_budget(self, metric_name: str) -> ErrorBudget | None:
        slo = self._slos.get(metric_name)
        events = self._events.get(metric_name)
        if slo is None or not events:
            return None
        measured = sum(events) / len(events)
        budget = max(1e-9, 1.0 - slo.objective)        # allowed bad fraction
        bad_fraction = 1.0 - measured
        consumed = bad_fraction / budget                # >1 => over budget
        window_fraction = len(events) / slo.window
        burn_rate = consumed / window_fraction if window_fraction > 0 else 0.0
        return ErrorBudget(
            slo=metric_name, objective=slo.objective, measured=measured,
            consumed=consumed, remaining=max(0.0, 1.0 - consumed), burn_rate=burn_rate,
        )

    def compliance_report(self) -> dict:
        """Compliance snapshot across all tracked SLOs."""
        out = {}
        for name in self._slos:
            sli = None
            events = self._events[name]
            if events:
                measured = sum(events) / len(events)
                sli = {"objective": self._slos[name].objective, "measured": round(measured, 4),
                       "met": measured >= self._slos[name].objective}
            eb = self.error_budget(name)
            out[name] = {"sli": sli, "error_budget": None if eb is None else {
                "consumed": round(eb.consumed, 4), "remaining": round(eb.remaining, 4),
                "burn_rate": round(eb.burn_rate, 3)}}
        return out

"""Configuration and data contracts for real-time quality monitoring.

Stdlib-only so the monitor runs in CI without numpy/sklearn (those are optional accelerators
for the ML detectors — see algorithms.py).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    """Incident severity. Lower = more severe (P1 is a page-now outage, P4 is informational)."""
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

    @property
    def label(self) -> str:
        return self.name


@dataclass
class MonitorConfig:
    window_size: int = 50           # rolling history length per metric
    min_samples: int = 10           # below this, detectors stay quiet (not enough data)
    zscore_threshold: float = 3.0   # |z| above this is anomalous
    iqr_k: float = 1.5              # Tukey fence multiplier
    ewma_alpha: float = 0.3         # smoothing for the trend-aware residual detector
    ewma_threshold: float = 3.0     # residual / residual-std above this is anomalous
    enable_ml: bool = True          # use Isolation Forest if sklearn is available
    seasonal_period: int = 24       # samples per cycle for seasonality checks


@dataclass
class QualityMetric:
    """One observation of a quality signal (e.g. faithfulness score, latency, error rate)."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    # Optional extra dimensions for multi-dimensional anomaly detection (e.g. per-model).
    dimensions: dict[str, float] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Anomaly:
    metric: str
    value: float
    method: str          # zscore | iqr | ewma | isolation_forest | multidim
    score: float         # method-specific strength (e.g. |z|)
    direction: str       # "high" | "low"
    severity: Severity
    message: str


@dataclass
class Alert:
    rule: str
    severity: Severity
    metric: str
    message: str
    timestamp: float = field(default_factory=time.time)
    escalation: list[str] = field(default_factory=list)


@dataclass
class SLIResult:
    name: str
    value: float         # measured indicator (0..1, e.g. fraction of good events)
    objective: float     # target
    met: bool


@dataclass
class ErrorBudget:
    slo: str
    objective: float
    measured: float
    consumed: float      # fraction of the budget used (0..1, >1 = over budget)
    remaining: float
    burn_rate: float     # consumption normalised by elapsed window fraction


@dataclass
class MonitoringResult:
    metric: str
    value: float
    is_anomaly: bool = False
    anomalies: list[Anomaly] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    sli: SLIResult | None = None
    error_budget: ErrorBudget | None = None
    investigation: dict | None = None
    healing_suggestions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "is_anomaly": self.is_anomaly,
            "anomalies": [
                {"method": a.method, "score": round(a.score, 3), "direction": a.direction,
                 "severity": a.severity.label, "message": a.message}
                for a in self.anomalies
            ],
            "alerts": [
                {"rule": al.rule, "severity": al.severity.label, "message": al.message,
                 "escalation": al.escalation}
                for al in self.alerts
            ],
            "sli": None if self.sli is None else {
                "name": self.sli.name, "value": round(self.sli.value, 4),
                "objective": self.sli.objective, "met": self.sli.met,
            },
            "error_budget": None if self.error_budget is None else {
                "slo": self.error_budget.slo, "consumed": round(self.error_budget.consumed, 4),
                "remaining": round(self.error_budget.remaining, 4),
                "burn_rate": round(self.error_budget.burn_rate, 3),
            },
            "investigation": self.investigation,
            "healing_suggestions": self.healing_suggestions,
        }

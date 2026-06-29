"""Dynamic threshold computation.

Static thresholds drift out of date as workloads change. These compute adaptive bounds from
recent history so alerting tracks the current normal rather than a hard-coded number.
"""
from __future__ import annotations

import statistics

from .algorithms import AnomalyDetector


def sigma_band(history: list[float], k: float = 3.0) -> tuple[float, float]:
    """Mean ± k·σ band."""
    if len(history) < 2:
        return (float("-inf"), float("inf"))
    mean, sd = statistics.fmean(history), statistics.pstdev(history)
    return (mean - k * sd, mean + k * sd)


def quantile_band(history: list[float], lo: float = 0.01, hi: float = 0.99) -> tuple[float, float]:
    """Empirical [lo, hi] quantile band — robust to non-normal distributions."""
    if not history:
        return (float("-inf"), float("inf"))
    q = AnomalyDetector._quantile
    return (q(history, lo), q(history, hi))


def dynamic_threshold(history: list[float], method: str = "sigma", **kw) -> tuple[float, float]:
    return quantile_band(history, **kw) if method == "quantile" else sigma_band(history, **kw)

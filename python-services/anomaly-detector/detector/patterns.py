"""Pattern recognition over metric time series: trend and seasonality.

These provide context that makes anomaly calls smarter — a rising trend or a seasonal trough
can explain a value that a naive point detector would flag.
"""
from __future__ import annotations

import statistics


def linear_trend(history: list[float]) -> tuple[str, float]:
    """Ordinary least-squares slope over the series. Returns (direction, slope_per_step)."""
    n = len(history)
    if n < 3:
        return ("stable", 0.0)
    xs = list(range(n))
    mx, my = statistics.fmean(xs), statistics.fmean(history)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return ("stable", 0.0)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, history)) / denom
    spread = statistics.pstdev(history) or 1e-9
    # Normalise the slope by spread so "significant" is scale-free.
    if slope > 0.05 * spread:
        return ("increasing", slope)
    if slope < -0.05 * spread:
        return ("decreasing", slope)
    return ("stable", slope)


def seasonality_strength(history: list[float], period: int) -> float:
    """Lag-`period` autocorrelation as a 0..1 seasonality strength (clamped)."""
    n = len(history)
    if period < 1 or n < 2 * period:
        return 0.0
    mean = statistics.fmean(history)
    var = sum((x - mean) ** 2 for x in history)
    if var == 0:
        return 0.0
    cov = sum((history[i] - mean) * (history[i - period] - mean) for i in range(period, n))
    return max(0.0, min(1.0, cov / var))


def is_seasonal(history: list[float], period: int, threshold: float = 0.5) -> bool:
    return seasonality_strength(history, period) >= threshold

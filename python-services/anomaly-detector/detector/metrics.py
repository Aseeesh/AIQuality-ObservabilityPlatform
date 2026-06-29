"""Rolling metric collection: bounded per-metric history feeding the detectors."""
from __future__ import annotations

from collections import deque

from .config import QualityMetric


class MetricCollector:
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self._series: dict[str, deque[float]] = {}
        self._latest: dict[str, QualityMetric] = {}

    def record(self, metric: QualityMetric) -> list[float]:
        """Append a metric and return the history *before* this point (for detection)."""
        series = self._series.setdefault(metric.name, deque(maxlen=self.window_size))
        history = list(series)
        series.append(metric.value)
        self._latest[metric.name] = metric
        return history

    def history(self, name: str) -> list[float]:
        return list(self._series.get(name, ()))

    def names(self) -> list[str]:
        return list(self._series)

    def latest(self, name: str) -> QualityMetric | None:
        return self._latest.get(name)

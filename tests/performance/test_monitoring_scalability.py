"""Performance: monitoring / anomaly detection.

Success metric: < 1s anomaly detection time per metric. Also checks the detector keeps up at a
high ingest rate (rolling-window detection is O(window), not O(history)).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import MetricSeriesFactory  # noqa: E402
from framework.harness import Suite, timed  # noqa: E402

from detector import MonitorConfig, QualityMetric  # noqa: E402
from detector.algorithms import AnomalyDetector  # noqa: E402

DETECTOR = AnomalyDetector(MonitorConfig())
HISTORY = MetricSeriesFactory.baseline(0.9, 50)
DETECT_BUDGET_MS = 1000


def test_detection_latency_under_budget():
    ms = timed(lambda: DETECTOR.detect(QualityMetric("quality", 0.2), HISTORY), iterations=200)
    print(f"    detection latency: {ms:.3f} ms")
    assert ms < DETECT_BUDGET_MS


def test_ingest_throughput():
    import time
    start = time.perf_counter()
    n = 5000
    for i in range(n):
        DETECTOR.detect(QualityMetric("quality", 0.9), HISTORY)
    rps = n / (time.perf_counter() - start)
    print(f"    detection throughput: {rps:.0f} points/s")
    assert rps > 1000


if __name__ == "__main__":
    raise SystemExit(0 if Suite("monitoring-scalability").run(globals()) == 0 else 1)

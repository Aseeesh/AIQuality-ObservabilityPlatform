"""Tests for the real-time QualityMonitor (stdlib only).

Run: ``python tests/test_monitor.py`` (or pytest).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detector import (  # noqa: E402
    AlertManager, MonitorConfig, QualityMetric, QualityMonitor, Severity, SLOTracker,
)
from detector.algorithms import AnomalyDetector  # noqa: E402
from detector.patterns import is_seasonal, linear_trend  # noqa: E402


def _warm(monitor: QualityMonitor, name: str, value: float, n: int = 20):
    # Feed a realistically jittered baseline (constant series have zero variance and would
    # degenerately silence the variance-based detectors).
    for i in range(n):
        monitor.monitor_sync(QualityMetric(name, value + (0.01 if i % 2 else -0.01)))


def _noisy(value: float, n: int = 30) -> list[float]:
    return [value + (0.01 if i % 2 else -0.01) for i in range(n)]


def test_stable_series_has_no_anomaly():
    m = QualityMonitor()
    _warm(m, "quality-score", 0.9, 20)
    res = m.monitor_sync(QualityMetric("quality-score", 0.9))
    assert not res.is_anomaly
    assert res.alerts == []


def test_spike_is_detected_and_alerts():
    m = QualityMonitor()
    _warm(m, "quality-score", 0.9, 25)
    res = m.monitor_sync(QualityMetric("quality-score", 0.2))  # sharp drop
    assert res.is_anomaly
    assert any(a.direction == "low" for a in res.anomalies)
    assert res.alerts  # at least one alert fired
    assert res.investigation is not None
    assert res.healing_suggestions


def test_severity_escalates_with_detector_consensus():
    det = AnomalyDetector(MonitorConfig())
    history = _noisy(0.9, 30)
    anomalies = det.detect(QualityMetric("quality-score", 0.1), history)
    # Multiple detectors should fire on a gross outlier and escalate toward P1.
    assert len(anomalies) >= 2
    assert min(a.severity for a in anomalies) <= Severity.P2


def test_multidimensional_anomaly():
    det = AnomalyDetector(MonitorConfig())
    history = [1.0] * 20
    metric = QualityMetric("ensemble", 1.0, dimensions={"m1": 3.5, "m2": 2.0})
    anomalies = det.detect(metric, history)
    assert any(a.method == "multidim" for a in anomalies)


def test_slo_error_budget_burns_on_bad_events():
    tracker = SLOTracker()
    for _ in range(50):
        tracker.record("quality-score", 0.95)   # good
    good_budget = tracker.error_budget("quality-score")
    for _ in range(50):
        tracker.record("quality-score", 0.5)    # bad (below 0.8 threshold)
    bad_budget = tracker.error_budget("quality-score")
    assert bad_budget.consumed > good_budget.consumed
    assert bad_budget.remaining < good_budget.remaining


def test_alert_cooldown_dedupes():
    fired = []
    mgr = AlertManager(on_call=fired.append, cooldown_seconds=999)
    m = QualityMonitor(alerts=mgr)
    _warm(m, "quality-score", 0.9, 25)
    m.monitor_sync(QualityMetric("quality-score", 0.1))
    first = len(fired)
    m.monitor_sync(QualityMetric("quality-score", 0.1))  # within cooldown
    assert len(fired) == first  # no duplicate page


def test_trend_and_seasonality_helpers():
    assert linear_trend([1, 2, 3, 4, 5, 6])[0] == "increasing"
    assert linear_trend([5, 5, 5, 5, 5])[0] == "stable"
    season = [0, 1, 0, 1, 0, 1, 0, 1]
    assert is_seasonal(season, period=2)


def test_mcp_tools_callable():
    m = QualityMonitor()
    _warm(m, "quality-score", 0.9, 12)
    tools = {t["name"]: t for t in m.mcp_tools()}
    assert "check_metric" in tools and "slo_status" in tools
    out = tools["check_metric"]["handler"](name="quality-score", value=0.9)
    assert out["metric"] == "quality-score"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

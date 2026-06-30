"""Quality validation: SLO tracking and error-budget accounting (detector SLOTracker).

The .NET SLOService is covered by xUnit; this validates the Python SLO reference implementation
used by the monitoring service and the MCP check_slo tool.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.harness import Suite  # noqa: E402

from detector import SLOTracker  # noqa: E402


def test_healthy_when_within_objective():
    t = SLOTracker()
    for _ in range(100):
        t.record("quality-score", 0.95)        # >= 0.8 => good
    sli = t.record("quality-score", 0.95)
    assert sli.met
    budget = t.error_budget("quality-score")
    assert budget.remaining > 0.9


def test_budget_burns_as_bad_events_accumulate():
    t = SLOTracker()
    for _ in range(50):
        t.record("quality-score", 0.95)
    before = t.error_budget("quality-score").consumed
    for _ in range(50):
        t.record("quality-score", 0.4)         # bad
    after = t.error_budget("quality-score").consumed
    assert after > before


def test_burn_rate_increases_under_sustained_failure():
    t = SLOTracker()
    for _ in range(100):
        t.record("latency-ms", 5000)           # all breach the 2000ms boundary
    eb = t.error_budget("latency-ms")
    assert eb.consumed > 1                       # over budget
    assert eb.burn_rate > 1


def test_compliance_report_covers_all_slos():
    t = SLOTracker()
    t.record("quality-score", 0.9)
    t.record("latency-ms", 500)
    report = t.compliance_report()
    assert "quality-score" in report and "latency-ms" in report


if __name__ == "__main__":
    raise SystemExit(0 if Suite("slo-tracking").run(globals()) == 0 else 1)

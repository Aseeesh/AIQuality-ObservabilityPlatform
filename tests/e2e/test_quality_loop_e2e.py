"""End-to-end: the full quality loop across services, in-process.

Scenario: bad outputs ship -> feedback comes in -> a benchmark flags low quality -> the gate
fails -> monitoring sees the anomaly -> an incident is opened and root-caused -> the improvement
agent proposes a fix. This is the platform's core value proposition exercised as one flow.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import EvalItemFactory, FeedbackFactory, IncidentEvidenceFactory, MetricSeriesFactory  # noqa: E402
from framework.harness import Suite  # noqa: E402

from processor import FeedbackProcessor, UserFeedback  # noqa: E402  (feedback-processor package)
from mcp import build_server  # noqa: E402
from mcp.automations import QualityAutomation, Trigger  # noqa: E402


def test_feedback_to_eval_case():
    proc = FeedbackProcessor()
    processed = proc.process_sync(UserFeedback(**FeedbackFactory.negative("accuracy")))
    # Negative feedback becomes a labelled "bad" eval case feeding the next gate.
    assert processed.eval_case is not None and processed.eval_case.label == "bad"
    assert processed.insights  # actionable improvement lever


def test_benchmark_flags_low_quality_and_gate_fails():
    server = build_server()
    bad = server.call_tool("run_benchmark", items=EvalItemFactory.batch(5, good=False))
    gate = server.call_tool("check_gate", metrics={"overall": bad["mean_overall"], "safety": 1.0})
    assert not gate["passed"]


def test_anomaly_opens_and_root_causes_incident():
    server = build_server()
    qa = QualityAutomation(server)
    # Monitoring detects the drop ...
    mon = server.agents.monitoring.run(name="quality", value=0.15, history=MetricSeriesFactory.baseline(0.9, 20))
    assert "raise_incident" in mon.actions
    # ... and the incident-response automation triages + root-causes it.
    results = qa.execute_sync(Trigger("anomaly_detected", payload=IncidentEvidenceFactory.dependency_timeout()))
    rca = next(o for o in results[0].outcomes if o.action == "triage_incident").result["data"]["rca"]
    assert "open_incident" in rca["root_cause"]


def test_improvement_agent_proposes_fix():
    server = build_server()
    res = server.agents.improvement.run(items=EvalItemFactory.batch(4, good=False), target=0.85)
    assert "open_improvement_plan" in res.actions
    assert res.data["suggestions"]


if __name__ == "__main__":
    raise SystemExit(0 if Suite("quality-loop-e2e").run(globals()) == 0 else 1)

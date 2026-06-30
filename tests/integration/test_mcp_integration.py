"""Integration: MCP tool registration, agent interaction, and automation execution.

Exercises the server as a whole (tools + agents + automations wired to the real services),
which is the integration boundary the dashboard and CI automations depend on.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import IncidentEvidenceFactory, MetricSeriesFactory  # noqa: E402
from framework.harness import Suite  # noqa: E402

from mcp import build_server  # noqa: E402
from mcp.automations import QualityAutomation, Trigger  # noqa: E402


def test_all_tool_categories_registered():
    server = build_server()
    cats = {t["category"] for t in server.list_tools()}
    assert {"quality", "monitoring", "incident", "automation"} <= cats


def test_agent_interaction_quality_then_gate():
    server = build_server()
    res = server.agents.quality.run(
        prompt="q", output="The availability target is 99.9 percent over 30 days.",
        context="availability target is 99.9 percent over 30 days")
    assert "evaluation" in res.data and "gate" in res.data


def test_monitoring_agent_to_incident_handoff():
    server = build_server()
    hist = MetricSeriesFactory.baseline(0.9, 20)
    res = server.agents.monitoring.run(name="quality", value=0.15, history=hist)
    assert "raise_incident" in res.actions


def test_automation_execution_end_to_end():
    server = build_server()
    qa = QualityAutomation(server)
    payload = IncidentEvidenceFactory.dependency_timeout()
    results = qa.execute_sync(Trigger("anomaly_detected", payload=payload))
    assert results and results[0].status == "success"
    triage = next(o for o in results[0].outcomes if o.action == "triage_incident")
    assert "incident" in triage.result.get("data", {})


def test_gate_automation_rolls_back_on_failure():
    server = build_server()
    qa = QualityAutomation(server)
    res = qa.execute_sync(Trigger("evaluation_complete",
        payload={"candidate": "rel-9", "metrics": {"overall": 0.4, "safety": 0.5}}))[0]
    actions = {o.action: o for o in res.outcomes}
    assert actions["rollback"].result.get("rolled_back") == "rel-9"


if __name__ == "__main__":
    raise SystemExit(0 if Suite("mcp-integration").run(globals()) == 0 else 1)

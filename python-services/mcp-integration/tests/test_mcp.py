"""Tests for the Quality MCP server (stdlib only; integrates sibling services if present).

Run: ``python tests/test_mcp.py`` (or pytest).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import build_server  # noqa: E402


def _server():
    return build_server()


def test_manifest_registers_all_tool_categories():
    s = _server()
    cats = {t["category"] for t in s.list_tools()}
    assert {"quality", "monitoring", "incident"} <= cats
    names = set(s.tools.names())
    assert {"evaluate_output", "check_gate", "run_benchmark", "analyze_trace", "detect_anomaly"} <= names
    assert {"check_slo", "get_metrics", "query_dashboard"} <= names
    assert {"create_incident", "escalate_incident", "resolve_incident", "postmortem_analyze"} <= names


def test_evaluate_output_tool():
    s = _server()
    out = s.call_tool("evaluate_output", prompt="What is the SLO?",
                      output="The availability target is 99.9 percent over 30 days.",
                      context="availability target is 99.9 percent over 30 days")
    assert "verdict" in out and "overall" in out


def test_detect_anomaly_tool():
    s = _server()
    history = [0.9 + (0.01 if i % 2 else -0.01) for i in range(20)]
    out = s.call_tool("detect_anomaly", name="quality", value=0.2, history=history)
    assert out["is_anomaly"] is True


def test_analyze_trace_tool_finds_originating_error():
    s = _server()
    spans = [
        {"span_id": "root", "operation": "Chat Request", "duration_ms": 6800, "status": "error"},
        {"span_id": "tool", "operation": "MCP Tool", "duration_ms": 5200, "status": "error", "parent_id": "root"},
    ]
    out = s.call_tool("analyze_trace", spans=spans)
    assert out["originating_error"] == "MCP Tool"
    assert out["error_count"] == 2


def test_incident_tools_lifecycle_and_rca():
    s = _server()
    inc = s.call_tool("create_incident", title="Tool timeout", severity="P1")
    assert inc["status"] == "open"
    pm = s.call_tool("postmortem_analyze", incident_id=inc["id"], traces=[
        {"span_id": "root", "operation": "Chat Request", "duration_ms": 6000, "status": "error"},
        {"span_id": "tool", "operation": "open_incident", "duration_ms": 5200, "status": "error",
         "parent_id": "root", "ai_kind": "mcp_tool_call", "error": "timeout"},
    ])
    assert "root_cause" in pm
    resolved = s.call_tool("resolve_incident", incident_id=inc["id"], resolution="added retry")
    assert resolved["status"] == "resolved"


def test_registry_validates_required_args():
    s = _server()
    try:
        s.call_tool("evaluate_output", prompt="only prompt")  # missing 'output'
        assert False, "expected ValueError"
    except ValueError as e:
        assert "output" in str(e)


def test_quality_agent_runs_eval_then_gate():
    s = _server()
    res = s.agents.quality.run(prompt="q", output="The availability target is 99.9 percent over 30 days.",
                               context="availability target is 99.9 percent over 30 days")
    assert "gate" in res.data and "evaluation" in res.data


def test_monitoring_agent_raises_incident_action_on_anomaly():
    s = _server()
    history = [0.9 + (0.01 if i % 2 else -0.01) for i in range(20)]
    res = s.agents.monitoring.run(name="quality", value=0.15, history=history)
    assert "raise_incident" in res.actions


def test_incident_agent_creates_and_escalates():
    s = _server()
    res = s.agents.incident.run(
        title="Quality drop", severity="P1",
        traces=[{"span_id": "tool", "operation": "open_incident", "duration_ms": 5200,
                 "status": "error", "ai_kind": "mcp_tool_call", "error": "timeout"}])
    assert "create_incident" in res.actions and "postmortem_analyze" in res.actions


def test_improvement_agent_flags_below_target():
    s = _server()
    items = [{"prompt": "q", "output": "bad", "context": "the real grounded answer about budgets"}] * 4
    res = s.agents.improvement.run(items=items, target=0.85)
    assert res.data["benchmark"]["count"] == 4
    assert "open_improvement_plan" in res.actions


def test_automation_fires_on_anomaly():
    s = _server()
    results = s.automations.fire("anomaly_detected", {"title": "spike", "severity": "P1",
        "traces": [{"span_id": "tool", "operation": "open_incident", "duration_ms": 5200,
                    "status": "error", "ai_kind": "mcp_tool_call", "error": "timeout"}]})
    assert results and results[0].triggered
    assert s.automations.list()  # automations registered


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

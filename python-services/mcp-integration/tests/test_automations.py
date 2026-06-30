"""Tests for AI quality automations (stdlib only).

Run: ``python tests/test_automations.py`` (or pytest).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import build_server  # noqa: E402
from mcp.automations import AutomationConfig, QualityAutomation, Trigger  # noqa: E402


def _auto(config=None):
    return QualityAutomation(build_server(), config)


def test_gate_pass_promotes():
    auto = _auto()
    res = auto.execute_sync(Trigger("evaluation_complete", payload={
        "candidate": "release-42", "metrics": {"overall": 0.92, "safety": 1.0}}))
    assert len(res) == 1
    actions = {o.action: o for o in res[0].outcomes}
    assert actions["promote"].result.get("promoted") == "release-42"
    assert actions["rollback"].result.get("skipped")
    assert res[0].status == "success"


def test_gate_fail_rolls_back():
    auto = _auto()
    res = auto.execute_sync(Trigger("evaluation_complete", payload={
        "candidate": "release-43", "metrics": {"overall": 0.4, "safety": 0.5}}))
    actions = {o.action: o for o in res[0].outcomes}
    assert actions["rollback"].result.get("rolled_back") == "release-43"
    assert actions["promote"].result.get("skipped")


def test_dry_run_simulates_side_effects():
    auto = _auto(AutomationConfig(dry_run=True))
    res = auto.execute_sync(Trigger("evaluation_complete", payload={
        "candidate": "r", "metrics": {"overall": 0.4}}))
    actions = {o.action: o for o in res[0].outcomes}
    assert actions["rollback"].result.get("simulated") is True


def test_monitoring_automation_investigates_anomaly():
    auto = _auto()
    history = [0.9 + (0.01 if i % 2 else -0.01) for i in range(20)]
    res = auto.execute_sync(Trigger("metric_received", payload={
        "name": "quality", "value": 0.15, "history": history, "severity": "P1"}))
    actions = {o.action: o for o in res[0].outcomes}
    assert "incident" in actions["investigate"].result.get("data", {}) or \
        actions["investigate"].result.get("agent") == "incident-agent"
    assert actions["self_heal"].result.get("suggestions")


def test_improvement_automation_below_target_starts_ab_test():
    auto = _auto()
    items = [{"prompt": "q", "output": "bad", "context": "grounded answer about error budgets"}] * 4
    res = auto.execute_sync(Trigger("benchmark_complete", payload={"items": items, "target": 0.85}))
    actions = {o.action: o for o in res[0].outcomes}
    assert "experiment" in actions["start_ab_test"].result


def test_incident_response_automation_triages_and_recommends():
    auto = _auto()
    res = auto.execute_sync(Trigger("anomaly_detected", payload={
        "title": "Tool timeout", "severity": "P1",
        "traces": [{"span_id": "tool", "operation": "open_incident", "duration_ms": 5200,
                    "status": "error", "ai_kind": "mcp_tool_call", "error": "timeout"}]}))
    actions = {o.action: o for o in res[0].outcomes}
    assert "incident" in actions["triage_incident"].result.get("data", {})
    assert actions["recommend_remediation"].result.get("recommendation")


def test_monitor_records_stats():
    auto = _auto()
    auto.execute_sync(Trigger("evaluation_complete", payload={"metrics": {"overall": 0.9}}))
    auto.execute_sync(Trigger("evaluation_complete", payload={"metrics": {"overall": 0.3}}))
    stats = auto.monitor.stats()
    assert stats["total"] == 2
    assert "success_rate" in stats


def test_automation_tools_registered_on_server():
    server = build_server()
    names = set(server.tools.names())
    assert {"list_automations", "run_automation"} <= names
    out = server.call_tool("run_automation", event="evaluation_complete",
                           payload={"candidate": "c", "metrics": {"overall": 0.95, "safety": 1.0}})
    assert out and out[0]["status"] in ("success", "skipped")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

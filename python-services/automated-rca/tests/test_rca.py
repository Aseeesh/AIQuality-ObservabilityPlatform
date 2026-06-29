"""Tests for automated root cause analysis (stdlib only, LLM disabled).

Run: ``python tests/test_rca.py`` (or pytest).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rca import (  # noqa: E402
    IncidentManager, LogEntry, MetricPoint, RCAConfig, RootCauseAnalyzer, Severity, SpanRecord,
)

CONFIG = RCAConfig(enable_llm=False)


def _failing_incident(mgr: IncidentManager):
    # Chat request where an MCP tool times out -> request fails (cascading), with matching
    # error logs, a latency spike metric, and a correlated deploy.
    traces = [
        SpanRecord("root", "Chat Request", 6800, status="error", parent_id=None),
        SpanRecord("retr", "Knowledge Retrieval", 95, status="ok", parent_id="root", ai_kind="retrieval"),
        SpanRecord("tool", "MCP Tool: open_incident", 5200, status="error", parent_id="root",
                   ai_kind="mcp_tool_call", error="downstream tool timed out"),
    ]
    logs = [
        LogEntry("open_incident timed out after 5001ms", level="ERROR"),
        LogEntry("open_incident timed out after 4998ms", level="ERROR"),
    ]
    metrics = [MetricPoint("latency_p95_ms", value=6800, baseline=2000)]
    return mgr.create("Incident tool failing", signals={"recent_deploy": "v1.4.2"},
                      traces=traces, logs=logs, metrics=metrics)


def test_severity_classification():
    mgr = IncidentManager()
    inc = _failing_incident(mgr)
    # 2 error spans + latency deviation 2.4x => at least P2 (here P1 via deviation >= 1.0).
    assert inc.severity in (Severity.P1, Severity.P2)


def test_root_cause_is_originating_dependency_failure():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = _failing_incident(analyzer.incidents)
    report = analyzer.analyze_sync(inc)

    assert report.category in ("dependency_failure",)
    assert "open_incident" in report.root_cause
    top = report.hypotheses[0]
    assert top.root_cause_span_id == "tool"
    assert top.confidence >= CONFIG.min_confidence


def test_evidence_collected():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = _failing_incident(analyzer.incidents)
    report = analyzer.analyze_sync(inc)
    ev = report.evidence
    assert ev is not None
    assert ev.originating_error.span_id == "tool"
    assert len(ev.error_spans) == 2
    assert any("latency" in m.name for m in ev.anomalous_metrics)
    assert ev.correlated_changes  # the deploy
    # Two timeout logs differing only by milliseconds cluster into one signature.
    assert any(count == 2 for count in ev.log_clusters.values())


def test_recommendations_present_and_prioritised():
    analyzer = RootCauseAnalyzer(CONFIG)
    report = analyzer.analyze_sync(_failing_incident(analyzer.incidents))
    assert report.recommendations
    assert any(r.priority == "high" for r in report.recommendations)


def test_patterns_and_knowledge_base():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = _failing_incident(analyzer.incidents)
    report = analyzer.analyze_sync(inc)
    # Knowledge-base resolution should be appended to the narrative.
    assert "Known resolutions" in report.narrative


def test_inconclusive_when_no_evidence():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = analyzer.incidents.create("Empty incident")
    report = analyzer.analyze_sync(inc)
    assert report.category == "inconclusive"
    assert report.recommendations  # still suggests gathering telemetry


def test_mcp_tools_analyze_by_id():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = _failing_incident(analyzer.incidents)
    tools = {t["name"]: t for t in analyzer.mcp_tools()}
    out = tools["analyze_incident"]["handler"](incident_id=inc.id)
    assert out["incident_id"] == inc.id
    kb = tools["knowledge_lookup"]["handler"](patterns=["dependency_timeout"])
    assert kb and kb[0]["pattern"] == "dependency_timeout"


def test_post_incident_review():
    analyzer = RootCauseAnalyzer(CONFIG)
    inc = _failing_incident(analyzer.incidents)
    report = analyzer.analyze_sync(inc)
    review = analyzer.incidents.post_incident_review(inc, report)
    assert review["incident_id"] == inc.id
    assert review["action_items"]


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

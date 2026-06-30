"""Performance: MCP tool execution latency.

Success metric: < 100ms tool execution time. Covers a representative tool from each category.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import MetricSeriesFactory, TraceFactory  # noqa: E402
from framework.harness import Suite, timed  # noqa: E402

from mcp import build_server  # noqa: E402

SERVER = build_server()
TOOL_BUDGET_MS = 100


def test_check_gate_latency():
    ms = timed(lambda: SERVER.call_tool("check_gate", metrics={"overall": 0.9}), iterations=500)
    print(f"    check_gate: {ms:.3f} ms")
    assert ms < TOOL_BUDGET_MS


def test_detect_anomaly_latency():
    hist = MetricSeriesFactory.baseline(0.9, 30)
    ms = timed(lambda: SERVER.call_tool("detect_anomaly", name="quality", value=0.2, history=hist), iterations=200)
    print(f"    detect_anomaly: {ms:.3f} ms")
    assert ms < TOOL_BUDGET_MS


def test_analyze_trace_latency():
    spans = TraceFactory.failing_trace()
    ms = timed(lambda: SERVER.call_tool("analyze_trace", spans=spans), iterations=200)
    print(f"    analyze_trace: {ms:.3f} ms")
    assert ms < TOOL_BUDGET_MS


def test_create_incident_latency():
    ms = timed(lambda: SERVER.call_tool("create_incident", title="perf", severity="P3"), iterations=500)
    print(f"    create_incident: {ms:.3f} ms")
    assert ms < TOOL_BUDGET_MS


if __name__ == "__main__":
    raise SystemExit(0 if Suite("mcp-tool-latency").run(globals()) == 0 else 1)

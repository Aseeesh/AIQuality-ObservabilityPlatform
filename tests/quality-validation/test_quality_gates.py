"""Quality validation: quality gates via the MCP check_gate tool (the cross-service surface)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.harness import Suite  # noqa: E402

from mcp import build_server  # noqa: E402

SERVER = build_server()


def test_gate_passes_when_metrics_meet_thresholds():
    out = SERVER.call_tool("check_gate", metrics={"overall": 0.92, "safety": 1.0})
    assert out["passed"] and out["status"] == "Passed"


def test_gate_fails_and_reports_failures():
    out = SERVER.call_tool("check_gate", metrics={"overall": 0.4, "safety": 0.5})
    assert not out["passed"]
    failing = {f["metric"] for f in out["failures"]}
    assert "overall" in failing and "safety" in failing


def test_custom_thresholds_respected():
    out = SERVER.call_tool("check_gate", metrics={"overall": 0.7}, thresholds={"overall": 0.6})
    assert out["passed"]


def test_run_benchmark_gate_separates_good_and_bad_batches():
    from framework import EvalItemFactory
    good = SERVER.call_tool("run_benchmark", items=EvalItemFactory.batch(5, good=True))
    bad = SERVER.call_tool("run_benchmark", items=EvalItemFactory.batch(5, good=False))
    assert good["mean_overall"] > bad["mean_overall"]


if __name__ == "__main__":
    raise SystemExit(0 if Suite("quality-gates").run(globals()) == 0 else 1)

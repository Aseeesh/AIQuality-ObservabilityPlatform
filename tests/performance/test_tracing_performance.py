"""Performance: trace analysis (RCA evidence collection over a span tree).

The .NET tracing hot path has its own benchmarks; this guards the Python trace-analysis path
(used by RCA and the MCP analyze_trace tool) — it must stay linear in the number of spans.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import TraceFactory  # noqa: E402
from framework.harness import Suite, timed  # noqa: E402

from mcp import build_server  # noqa: E402

SERVER = build_server()


def test_small_trace_analysis_is_fast():
    spans = TraceFactory.failing_trace()
    ms = timed(lambda: SERVER.call_tool("analyze_trace", spans=spans), iterations=200)
    print(f"    analyze_trace (3 spans): {ms:.3f} ms")
    assert ms < 50


def test_large_trace_scales_linearly():
    small = TraceFactory.healthy_trace(10)
    large = TraceFactory.healthy_trace(200)
    ms_small = timed(lambda: SERVER.call_tool("analyze_trace", spans=small), iterations=50)
    ms_large = timed(lambda: SERVER.call_tool("analyze_trace", spans=large), iterations=50)
    print(f"    10 spans: {ms_small:.3f} ms, 200 spans: {ms_large:.3f} ms")
    # 20x the spans should cost well under 50x the time (i.e. not quadratic).
    assert ms_large < ms_small * 50 + 5


if __name__ == "__main__":
    raise SystemExit(0 if Suite("tracing-performance").run(globals()) == 0 else 1)

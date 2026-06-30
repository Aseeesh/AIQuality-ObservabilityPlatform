"""Test data factories — deterministic builders for the platform's domain objects.

Factories return plain dicts (portable across services and HTTP) plus a few typed builders for
convenience. Determinism (seeded jitter) keeps performance/validation assertions stable.
"""
from __future__ import annotations


class EvalItemFactory:
    """Evaluation items (prompt/output/context/references)."""

    @staticmethod
    def grounded(i: int = 0) -> dict:
        return {
            "prompt": "Describe the API availability SLO.",
            "context": "API availability target is 99.9 percent over a 30 day window using error budgets.",
            "output": f"The API availability target is 99.9 percent over a rolling 30 day window number {i}, "
                      "tracked with error budgets and burn-rate alerts.",
            "references": ["https://docs/slo"],
        }

    @staticmethod
    def ungrounded(i: int = 0) -> dict:
        return {
            "prompt": "Describe the API availability SLO.",
            "context": "API availability target is 99.9 percent over a 30 day window.",
            "output": "Availability is whatever the aliens decide.",
            "references": [],
        }

    @classmethod
    def batch(cls, n: int, good: bool = True) -> list[dict]:
        f = cls.grounded if good else cls.ungrounded
        return [f(i) for i in range(n)]


class TraceFactory:
    """Trace span trees (as dicts compatible with analyze_trace / RCA)."""

    @staticmethod
    def failing_trace() -> list[dict]:
        return [
            {"span_id": "root", "operation": "Chat Request", "duration_ms": 6800, "status": "error"},
            {"span_id": "retr", "operation": "Knowledge Retrieval", "duration_ms": 95,
             "status": "ok", "parent_id": "root", "ai_kind": "retrieval"},
            {"span_id": "tool", "operation": "MCP Tool: open_incident", "duration_ms": 5200,
             "status": "error", "parent_id": "root", "ai_kind": "mcp_tool_call", "error": "downstream timed out"},
        ]

    @staticmethod
    def healthy_trace(n_children: int = 5) -> list[dict]:
        spans = [{"span_id": "root", "operation": "Chat Request", "duration_ms": 1000, "status": "ok"}]
        for i in range(n_children):
            spans.append({"span_id": f"c{i}", "operation": f"step-{i}", "duration_ms": 50 + i,
                          "status": "ok", "parent_id": "root"})
        return spans


class MetricSeriesFactory:
    """Deterministic metric series with optional injected spikes."""

    @staticmethod
    def baseline(value: float, n: int = 30) -> list[float]:
        return [value + (0.01 if i % 2 else -0.01) for i in range(n)]

    @staticmethod
    def with_spike(value: float, spike: float, n: int = 30) -> list[float]:
        series = MetricSeriesFactory.baseline(value, n)
        series[-1] = spike
        return series


class FeedbackFactory:
    """User feedback events."""

    @staticmethod
    def negative(topic: str = "accuracy") -> dict:
        text = {"accuracy": "completely wrong and inaccurate",
                "latency": "far too slow", "completeness": "vague and incomplete"}.get(topic, "bad")
        return {"prompt": "q", "response": "a", "rating": 1, "text": text}

    @staticmethod
    def positive() -> dict:
        return {"prompt": "q", "response": "a clear, helpful answer", "rating": 5, "text": "great and helpful"}


class IncidentEvidenceFactory:
    """Bundles of incident evidence (traces/logs/metrics) for RCA."""

    @staticmethod
    def dependency_timeout() -> dict:
        return {
            "title": "MCP tool timeout cascading failure",
            "severity": "P1",
            "signals": {"recent_deploy": "v1.4.2"},
            "traces": TraceFactory.failing_trace(),
            "logs": [
                {"message": "open_incident timed out after 5001ms", "level": "ERROR"},
                {"message": "open_incident timed out after 4998ms", "level": "ERROR"},
            ],
            "metrics": [{"name": "latency_p95_ms", "value": 6800, "baseline": 2000}],
        }

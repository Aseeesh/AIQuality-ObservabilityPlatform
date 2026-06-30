"""Mock services / fakes for isolating tests from external dependencies."""
from __future__ import annotations


class CannedJudge:
    """A judge backend that returns fixed scores — for testing pipeline wiring without a model."""

    def __init__(self, scores: dict[str, float] | None = None):
        self.scores = scores or {"accuracy": 0.9, "relevance": 0.9, "completeness": 0.9, "safety": 1.0}
        self.calls = 0

    def score(self, prompt: str, output: str, context: str = "") -> dict:
        self.calls += 1
        overall = sum(self.scores.values()) / len(self.scores)
        return {"scores": dict(self.scores), "overall": overall,
                "verdict": "Passed" if overall >= 0.8 else "Failed"}


class MockNotificationSink:
    """Captures notifications instead of paging real channels."""

    def __init__(self):
        self.sent: list[dict] = []

    def send(self, channel: str, target: str, message: str) -> dict:
        n = {"channel": channel, "target": target, "message": message}
        self.sent.append(n)
        return n

    def by_channel(self, channel: str) -> list[dict]:
        return [n for n in self.sent if n["channel"] == channel]


class FakeApiClient:
    """In-memory stand-in for the .NET API, so HTTP-shaped e2e tests run without a server.

    Implements just enough of the evaluation/SLO surface for the e2e quality loop; mirrors the
    real endpoints' shapes so a test can swap this for a real HTTP client unchanged.
    """

    def __init__(self):
        self._runs: list[dict] = []
        self._slo_events: dict[str, list[bool]] = {}

    def run_batch(self, dataset: str, items: list[dict]) -> dict:
        # Trivial grounded-overlap scorer mirroring the heuristic evaluator.
        def score(it: dict) -> float:
            ctx = {w.lower() for w in it.get("context", "").split() if len(w) > 3}
            out = {w.lower() for w in it.get("output", "").split() if len(w) > 3}
            return len(ctx & out) / len(ctx) if ctx else (0.7 if it.get("output") else 0.0)

        overalls = [score(i) for i in items]
        mean = sum(overalls) / len(overalls) if overalls else 0.0
        run = {"id": f"run-{len(self._runs)}", "dataset": dataset, "overall": mean,
               "passRate": sum(1 for o in overalls if o >= 0.8) / len(overalls) if overalls else 0.0}
        self._runs.append(run)
        return run

    def record_slo(self, name: str, good: bool) -> None:
        self._slo_events.setdefault(name, []).append(good)

    def slo_compliance(self, name: str) -> float:
        ev = self._slo_events.get(name, [])
        return sum(ev) / len(ev) if ev else 1.0

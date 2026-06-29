"""Generate remediation recommendations keyed off the root-cause category."""
from __future__ import annotations

from .config import EvidenceBundle, Hypothesis, Recommendation

# Category -> ordered remediations (most impactful first).
_PLAYBOOK: dict[str, list[tuple[str, str, str]]] = {
    "dependency_failure": [
        ("Add a timeout + retry with backoff around the failing dependency.",
         "The originating failure was a downstream call; resilience patterns contain it.", "high"),
        ("Add a circuit breaker and a degraded-mode fallback.",
         "Prevents the dependency from failing the whole request.", "high"),
    ],
    "operation_failure": [
        ("Inspect the failing span's inputs and add defensive handling.",
         "The operation errored at the root of the trace.", "high"),
    ],
    "performance": [
        ("Profile and optimise the bottleneck operation (cache, batch, or parallelise).",
         "One span dominates latency.", "high"),
        ("Scale out capacity or raise concurrency limits.",
         "Relieves latency under load.", "medium"),
    ],
    "quality_regression": [
        ("Roll back the prompt/model version to the last known-good baseline.",
         "Quality dropped against baseline.", "high"),
        ("Run a batch re-evaluation to scope the regression and gate further rollout.",
         "Quantifies blast radius before more traffic is affected.", "medium"),
    ],
    "change_induced": [
        ("Roll back or feature-flag off the correlated recent change.",
         "A change is time-correlated with the incident onset.", "high"),
    ],
    "error_pattern": [
        ("Address the most frequent error signature first.",
         "A single recurring error dominates the logs.", "medium"),
    ],
}


class RecommendationEngine:
    def for_hypotheses(self, hypotheses: list[Hypothesis], evidence: EvidenceBundle) -> list[Recommendation]:
        recs: list[Recommendation] = []
        seen: set[str] = set()
        # Recommend for the top hypotheses, de-duplicating identical actions.
        for h in hypotheses[:3]:
            for action, rationale, priority in _PLAYBOOK.get(h.category, []):
                if action in seen:
                    continue
                seen.add(action)
                recs.append(Recommendation(action, rationale, priority))
        if not recs:
            recs.append(Recommendation(
                "Gather more telemetry (traces/logs/metrics) around the incident window.",
                "Evidence was insufficient for a confident root cause.", "medium"))
        return recs

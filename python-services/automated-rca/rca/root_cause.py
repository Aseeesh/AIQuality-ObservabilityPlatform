"""Causal inference: generate and rank root-cause hypotheses from collected evidence.

Hypotheses are produced by evidence-driven rules, each carrying a confidence built from the
strength and corroboration of its evidence. Confidence is boosted when independent sources
agree (a failing span + matching error logs + a correlated deploy is far more convincing than
any one alone). The highest-confidence hypothesis becomes the root cause, unless it falls
below the configured floor (then the result is "inconclusive").
"""
from __future__ import annotations

from .config import EvidenceBundle, Hypothesis, Incident, RCAConfig


class CausalInferenceEngine:
    def __init__(self, config: RCAConfig | None = None):
        self.config = config or RCAConfig()

    def infer(self, incident: Incident, evidence: EvidenceBundle) -> list[Hypothesis]:
        hypotheses: list[Hypothesis] = []
        hypotheses += self._from_traces(evidence)
        hypotheses += self._from_metrics(evidence)
        hypotheses += self._from_changes(evidence)
        hypotheses += self._from_logs(evidence)

        self._corroborate(hypotheses, evidence)
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses[: self.config.max_hypotheses]

    # ---- evidence-specific hypothesis generators ----
    def _from_traces(self, e: EvidenceBundle) -> list[Hypothesis]:
        out: list[Hypothesis] = []
        if e.originating_error:
            s = e.originating_error
            kind = s.ai_kind or "operation"
            out.append(Hypothesis(
                description=f"'{s.operation}' ({kind}) failed and propagated up the trace.",
                category="dependency_failure" if kind == "mcp_tool_call" else "operation_failure",
                confidence=0.6,
                supporting_evidence=[f"originating error span '{s.operation}': {s.error or 'no detail'}"],
                root_cause_span_id=s.span_id,
            ))
        if e.bottleneck_span and e.bottleneck_span.duration_ms >= 1000 and e.bottleneck_span is not e.originating_error:
            b = e.bottleneck_span
            out.append(Hypothesis(
                description=f"'{b.operation}' is a latency bottleneck ({b.duration_ms:.0f} ms self-time).",
                category="performance",
                confidence=0.4,
                supporting_evidence=[f"bottleneck span '{b.operation}' dominates trace latency"],
                root_cause_span_id=b.span_id,
            ))
        return out

    def _from_metrics(self, e: EvidenceBundle) -> list[Hypothesis]:
        out: list[Hypothesis] = []
        for m in e.anomalous_metrics:
            name = m.name.lower()
            if "latency" in name or "error" in name:
                cat, desc = "performance", f"{m.name} spiked {m.deviation:+.0%} vs baseline."
            elif "quality" in name or "score" in name or "accuracy" in name:
                cat, desc = "quality_regression", f"{m.name} dropped {m.deviation:+.0%} vs baseline."
            else:
                cat, desc = "anomaly", f"{m.name} deviated {m.deviation:+.0%} vs baseline."
            out.append(Hypothesis(desc, cat, 0.45, [f"metric {m.name} deviation {m.deviation:+.0%}"]))
        return out

    def _from_changes(self, e: EvidenceBundle) -> list[Hypothesis]:
        return [
            Hypothesis(
                description=f"A recent change is the likely trigger ({change}).",
                category="change_induced",
                confidence=0.5,
                supporting_evidence=[f"time-correlated change: {change}"],
            )
            for change in e.correlated_changes
        ]

    def _from_logs(self, e: EvidenceBundle) -> list[Hypothesis]:
        if not e.log_clusters:
            return []
        sig, count = next(iter(e.log_clusters.items()))
        return [Hypothesis(
            description=f"Recurring error pattern: '{sig}' ({count}×).",
            category="error_pattern",
            confidence=min(0.55, 0.3 + 0.05 * count),
            supporting_evidence=[f"{count} matching error logs"],
        )]

    # ---- corroboration: agreement across sources raises confidence ----
    def _corroborate(self, hypotheses: list[Hypothesis], e: EvidenceBundle) -> None:
        has_change = bool(e.correlated_changes)
        has_logs = bool(e.log_clusters)
        has_metric = bool(e.anomalous_metrics)
        for h in hypotheses:
            boost = 0.0
            # A failing operation corroborated by error logs is much more convincing.
            if h.category in ("dependency_failure", "operation_failure") and has_logs:
                boost += 0.2
                h.supporting_evidence.append("corroborated by error logs")
            # A change-induced hypothesis corroborated by a metric/quality regression.
            if h.category == "change_induced" and (has_metric or has_logs):
                boost += 0.2
                h.supporting_evidence.append("corroborated by anomalous signals")
            if h.category == "performance" and has_metric:
                boost += 0.15
            if has_change and h.category != "change_induced":
                boost += 0.1  # a concurrent deploy makes any failure more suspicious
            h.confidence = min(0.99, h.confidence + boost)

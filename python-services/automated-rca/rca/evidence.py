"""Evidence collection: turn an incident's raw signals into structured evidence.

Four sources, mirroring what an on-call engineer would pull up:
  * Trace analysis   — error spans, the *originating* error (no errored ancestor), bottleneck.
  * Log analysis     — error/critical lines, clustered by message signature.
  * Metric correlation — metrics deviating from baseline beyond a threshold.
  * Context gathering — recent deploys/config changes that correlate in time.
"""
from __future__ import annotations

import re

from .config import EvidenceBundle, Incident, MetricPoint, RCAConfig, SpanRecord

_NUM = re.compile(r"\d+")
_HEX = re.compile(r"\b[0-9a-f]{8,}\b")


class EvidenceCollector:
    def __init__(self, config: RCAConfig | None = None):
        self.config = config or RCAConfig()

    def collect(self, incident: Incident) -> EvidenceBundle:
        bundle = EvidenceBundle()
        self._analyze_traces(incident.traces, bundle)
        self._analyze_logs(incident.logs, bundle)
        self._correlate_metrics(incident.metrics, bundle)
        self._gather_context(incident, bundle)
        self._build_timeline(incident, bundle)
        return bundle

    # ------------------------------------------------------------- trace analysis
    def _analyze_traces(self, spans: list[SpanRecord], bundle: EvidenceBundle) -> None:
        if not spans:
            return
        by_id = {s.span_id: s for s in spans}
        errors = [s for s in spans if s.status == "error"]
        bundle.error_spans = errors

        # Originating error: an error span with no errored ancestor (the deepest cause).
        ancestors_of_errors: set[str] = set()
        for e in errors:
            pid = e.parent_id
            while pid and pid in by_id:
                ancestors_of_errors.add(pid)
                pid = by_id[pid].parent_id
        originating = [e for e in errors if e.span_id not in ancestors_of_errors]
        bundle.originating_error = originating[0] if originating else (errors[0] if errors else None)

        # Bottleneck: span with the most self-time (own minus children).
        def self_time(s: SpanRecord) -> float:
            child = sum(c.duration_ms for c in spans if c.parent_id == s.span_id)
            return max(0.0, s.duration_ms - child)

        bundle.bottleneck_span = max(spans, key=self_time)

    # ------------------------------------------------------------- log analysis
    def _analyze_logs(self, logs: list[LogEntry], bundle: EvidenceBundle) -> None:  # type: ignore[name-defined]
        errors = [l for l in logs if l.level in ("ERROR", "CRITICAL")]
        bundle.log_errors = errors
        # Cluster by signature (strip numbers/hex so "timeout after 5001ms" == "after 4999ms").
        clusters: dict[str, int] = {}
        for entry in errors:
            sig = _HEX.sub("<id>", _NUM.sub("<n>", entry.message)).strip()
            clusters[sig] = clusters.get(sig, 0) + 1
        bundle.log_clusters = dict(sorted(clusters.items(), key=lambda kv: -kv[1]))

    # ------------------------------------------------------------- metric correlation
    def _correlate_metrics(self, metrics: list[MetricPoint], bundle: EvidenceBundle) -> None:
        bundle.anomalous_metrics = [
            m for m in metrics if abs(m.deviation) >= self.config.metric_deviation_threshold
        ]

    # ------------------------------------------------------------- context gathering
    def _gather_context(self, incident: Incident, bundle: EvidenceBundle) -> None:
        # Time-correlated change signals are strong root-cause candidates.
        for key in ("recent_deploy", "config_change", "feature_flag", "dependency_upgrade"):
            if key in incident.signals:
                bundle.correlated_changes.append(f"{key}: {incident.signals[key]}")

    # ------------------------------------------------------------- timeline
    def _build_timeline(self, incident: Incident, bundle: EvidenceBundle) -> None:
        events: list[str] = []
        for c in bundle.correlated_changes:
            events.append(f"change · {c}")
        if bundle.originating_error:
            e = bundle.originating_error
            events.append(f"error · {e.operation} failed ({e.error or 'no detail'})")
        for m in bundle.anomalous_metrics:
            events.append(f"metric · {m.name} {m.deviation:+.0%} vs baseline")
        for sig, n in list(bundle.log_clusters.items())[:3]:
            events.append(f"log · {n}× {sig}")
        bundle.timeline = events

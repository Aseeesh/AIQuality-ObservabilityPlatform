"""Configuration and data contracts for automated root cause analysis.

Stdlib-only so the analyzer runs offline; an LLM backend (Ollama/Anthropic) is optional and
only enriches the narrative — the causal inference itself is deterministic and explainable.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4

    @property
    def label(self) -> str:
        return self.name


# ---- Evidence inputs (collected from tracing, logging, and metrics subsystems) ----
@dataclass
class SpanRecord:
    span_id: str
    operation: str
    duration_ms: float
    status: str = "ok"               # "ok" | "error"
    parent_id: str | None = None
    service: str = "aiquality-api"
    ai_kind: str | None = None        # llm_call | mcp_tool_call | retrieval | ...
    error: str | None = None


@dataclass
class LogEntry:
    message: str
    level: str = "INFO"               # INFO | WARN | ERROR | CRITICAL
    service: str = "aiquality-api"
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetricPoint:
    name: str
    value: float
    baseline: float | None = None     # expected value; deviation drives correlation
    timestamp: float = field(default_factory=time.time)

    @property
    def deviation(self) -> float:
        if self.baseline is None or self.baseline == 0:
            return 0.0
        return (self.value - self.baseline) / abs(self.baseline)


@dataclass
class Incident:
    id: str
    title: str
    severity: Severity = Severity.P3
    description: str = ""
    started_at: float = field(default_factory=time.time)
    trace_id: str | None = None
    signals: dict[str, str] = field(default_factory=dict)   # e.g. recent_deploy, config_change
    traces: list[SpanRecord] = field(default_factory=list)
    logs: list[LogEntry] = field(default_factory=list)
    metrics: list[MetricPoint] = field(default_factory=list)


@dataclass
class RCAConfig:
    max_hypotheses: int = 5
    min_confidence: float = 0.3       # below this, root cause is "inconclusive"
    metric_deviation_threshold: float = 0.25  # |deviation| above this is anomalous
    enable_llm: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    anthropic_model: str = "claude-opus-4-8"


# ---- Analysis outputs ----
@dataclass
class EvidenceBundle:
    error_spans: list[SpanRecord] = field(default_factory=list)
    originating_error: SpanRecord | None = None
    bottleneck_span: SpanRecord | None = None
    log_errors: list[LogEntry] = field(default_factory=list)
    log_clusters: dict[str, int] = field(default_factory=dict)
    anomalous_metrics: list[MetricPoint] = field(default_factory=list)
    correlated_changes: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)


@dataclass
class Hypothesis:
    description: str
    category: str                     # dependency_failure | performance | quality_regression | ...
    confidence: float                 # 0..1
    supporting_evidence: list[str] = field(default_factory=list)
    root_cause_span_id: str | None = None


@dataclass
class Recommendation:
    action: str
    rationale: str
    priority: str = "medium"          # high | medium | low


@dataclass
class RCAReport:
    incident_id: str
    root_cause: str
    confidence: float
    category: str
    hypotheses: list[Hypothesis] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    evidence: EvidenceBundle | None = None
    narrative: str = ""

    def as_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "root_cause": self.root_cause,
            "category": self.category,
            "confidence": round(self.confidence, 3),
            "hypotheses": [
                {"description": h.description, "category": h.category,
                 "confidence": round(h.confidence, 3), "evidence": h.supporting_evidence,
                 "root_cause_span_id": h.root_cause_span_id}
                for h in self.hypotheses
            ],
            "recommendations": [
                {"action": r.action, "rationale": r.rationale, "priority": r.priority}
                for r in self.recommendations
            ],
            "evidence": None if self.evidence is None else {
                "originating_error": self.evidence.originating_error.operation if self.evidence.originating_error else None,
                "bottleneck": self.evidence.bottleneck_span.operation if self.evidence.bottleneck_span else None,
                "error_span_count": len(self.evidence.error_spans),
                "log_clusters": self.evidence.log_clusters,
                "anomalous_metrics": [m.name for m in self.evidence.anomalous_metrics],
                "correlated_changes": self.evidence.correlated_changes,
                "timeline": self.evidence.timeline,
            },
            "narrative": self.narrative,
        }

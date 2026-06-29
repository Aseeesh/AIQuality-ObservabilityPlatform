"""RootCauseAnalyzer orchestrator + FastAPI app.

Pipeline (RootCauseAnalyzer.analyze):
    incident ─▶ collect evidence (traces, logs, metrics, context)
             ─▶ recognise patterns
             ─▶ generate + rank hypotheses (causal inference, corroboration)
             ─▶ generate recommendations
             ─▶ narrate (LLM optional)
             ─▶ RCAReport

The FastAPI import is guarded so the module imports (and tests run) without fastapi installed;
the container entrypoint (``uvicorn rca.analyzer:app``) provides it.
"""
from __future__ import annotations

import asyncio

from .ai_analysis import AIAnalyzer
from .config import Incident, RCAConfig, RCAReport
from .evidence import EvidenceCollector
from .incident import IncidentManager
from .mcp_integration import MCPIntegration
from .recommendations import RecommendationEngine
from .reports import build_report
from .root_cause import CausalInferenceEngine


class RootCauseAnalyzer:
    """Automated root cause analysis with AI."""

    def __init__(self, config: RCAConfig | None = None):
        self.config = config or RCAConfig()
        self.evidence = EvidenceCollector(self.config)        # trace/log/metric evidence
        self.causal = CausalInferenceEngine(self.config)      # hypothesis generation + ranking
        self.analyzer = AIAnalyzer(self.config)               # pattern recognition + narrative
        self.recommender = RecommendationEngine()
        self.incidents = IncidentManager()
        self.mcp = MCPIntegration()

    async def analyze(self, incident: Incident) -> RCAReport:
        """Perform automated root cause analysis for an incident."""
        evidence = self.evidence.collect(incident)
        patterns = self.analyzer.recognize_patterns(evidence)
        hypotheses = self.causal.infer(incident, evidence)
        recommendations = self.recommender.for_hypotheses(hypotheses, evidence)
        narrative = self.analyzer.narrate(incident, evidence, hypotheses, patterns)
        report = build_report(incident, evidence, hypotheses, recommendations, narrative, self.config)
        # Attach knowledge-base resolutions for the recognised patterns.
        kb = self.mcp.knowledge_for(patterns)
        if kb:
            report.narrative += "\n\nKnown resolutions: " + "; ".join(k["resolution"] for k in kb)
        return report

    def analyze_sync(self, incident: Incident) -> RCAReport:
        return asyncio.run(self.analyze(incident))

    def mcp_tools(self) -> list[dict]:
        return self.mcp.tools(self)


# --------------------------------------------------------------------------- FastAPI
analyzer = RootCauseAnalyzer()

try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    class SpanIn(BaseModel):
        span_id: str
        operation: str
        duration_ms: float
        status: str = "ok"
        parent_id: str | None = None
        ai_kind: str | None = None
        error: str | None = None

    class LogIn(BaseModel):
        message: str
        level: str = "INFO"

    class MetricIn(BaseModel):
        name: str
        value: float
        baseline: float | None = None

    class IncidentIn(BaseModel):
        title: str
        description: str = ""
        trace_id: str | None = None
        signals: dict[str, str] = {}
        traces: list[SpanIn] = []
        logs: list[LogIn] = []
        metrics: list[MetricIn] = []

    app = FastAPI(title="AIQuality Automated RCA")

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    @app.post("/analyze")
    async def analyze_endpoint(body: IncidentIn) -> dict:
        from .config import LogEntry, MetricPoint, SpanRecord
        incident = analyzer.incidents.create(
            title=body.title, description=body.description, trace_id=body.trace_id,
            signals=body.signals,
            traces=[SpanRecord(**s.model_dump()) for s in body.traces],
            logs=[LogEntry(**l.model_dump()) for l in body.logs],
            metrics=[MetricPoint(**m.model_dump()) for m in body.metrics],
        )
        report = await analyzer.analyze(incident)
        return {"incident_id": incident.id, "severity": incident.severity.label, **report.as_dict()}

except Exception:  # pragma: no cover - fastapi not installed
    app = None  # type: ignore

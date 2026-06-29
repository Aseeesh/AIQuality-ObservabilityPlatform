"""MCP integration: RCA as agent-callable tools, with a small knowledge base.

Exposes the analyzer as MCP tools so a monitoring/incident agent can request a diagnosis,
and provides a knowledge base mapping known patterns to vetted resolutions — the
"automated diagnostics" an agent consults before proposing actions.
"""
from __future__ import annotations

from .config import RCAReport

# Knowledge base: incident pattern -> known resolution + a runbook link.
KNOWLEDGE_BASE: dict[str, dict[str, str]] = {
    "dependency_timeout": {
        "resolution": "Apply timeout+retry+circuit-breaker around the downstream tool.",
        "runbook": "docs/operations/dependency-timeouts.md",
    },
    "cascading_failure": {
        "resolution": "Isolate the originating failure; add bulkheads to stop propagation.",
        "runbook": "docs/operations/cascading-failures.md",
    },
    "quality_regression": {
        "resolution": "Roll back model/prompt; re-run evaluation gates before re-deploy.",
        "runbook": "docs/quality/regressions.md",
    },
    "latency_spike": {
        "resolution": "Scale out / optimise the bottleneck; check for noisy-neighbour load.",
        "runbook": "docs/operations/latency.md",
    },
    "change_induced": {
        "resolution": "Roll back or flag off the correlated change; verify recovery.",
        "runbook": "docs/operations/change-management.md",
    },
}


class MCPIntegration:
    def knowledge_for(self, patterns: list[str]) -> list[dict]:
        """Look up vetted resolutions for the recognised patterns."""
        out = []
        for p in patterns:
            if p in KNOWLEDGE_BASE:
                out.append({"pattern": p, **KNOWLEDGE_BASE[p]})
        return out

    def tools(self, analyzer) -> list[dict]:
        """MCP tool specs an agent can call against a RootCauseAnalyzer."""
        return [
            {
                "name": "analyze_incident",
                "description": "Run automated root cause analysis for an incident id and return the report.",
                "input_schema": {
                    "type": "object",
                    "properties": {"incident_id": {"type": "string"}},
                    "required": ["incident_id"],
                },
                "handler": lambda incident_id: _analyze_by_id(analyzer, incident_id),
            },
            {
                "name": "knowledge_lookup",
                "description": "Return known resolutions/runbooks for recognised incident patterns.",
                "input_schema": {
                    "type": "object",
                    "properties": {"patterns": {"type": "array", "items": {"type": "string"}}},
                    "required": ["patterns"],
                },
                "handler": lambda patterns: self.knowledge_for(patterns),
            },
        ]


def _analyze_by_id(analyzer, incident_id: str) -> dict:
    incident = analyzer.incidents._incidents.get(incident_id)  # type: ignore[attr-defined]
    if incident is None:
        return {"error": f"unknown incident {incident_id}"}
    return analyzer.analyze_sync(incident).as_dict()

"""Incident MCP tools: create_incident, escalate_incident, resolve_incident, postmortem_analyze."""
from __future__ import annotations

from ..config import ToolSpec
from ..providers import IncidentProvider


def build_incident_tools(provider: IncidentProvider) -> list[ToolSpec]:
    return [
        ToolSpec(
            name="create_incident",
            description="Open an incident with a title and severity.",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                    "description": {"type": "string"}, "signals": {"type": "object"},
                },
                "required": ["title"],
            },
            handler=provider.create_incident,
            category="incident",
        ),
        ToolSpec(
            name="escalate_incident",
            description="Escalate an incident to a team/on-call.",
            input_schema={
                "type": "object",
                "properties": {"incident_id": {"type": "string"}, "to": {"type": "string"}},
                "required": ["incident_id"],
            },
            handler=provider.escalate_incident,
            category="incident",
        ),
        ToolSpec(
            name="resolve_incident",
            description="Mark an incident resolved with a resolution note.",
            input_schema={
                "type": "object",
                "properties": {"incident_id": {"type": "string"}, "resolution": {"type": "string"}},
                "required": ["incident_id"],
            },
            handler=provider.resolve_incident,
            category="incident",
        ),
        ToolSpec(
            name="postmortem_analyze",
            description="Run automated root cause analysis for an incident from traces/logs/metrics.",
            input_schema={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string"},
                    "traces": {"type": "array", "items": {"type": "object"}},
                    "logs": {"type": "array", "items": {"type": "object"}},
                    "metrics": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["incident_id"],
            },
            handler=provider.postmortem_analyze,
            category="incident",
        ),
    ]

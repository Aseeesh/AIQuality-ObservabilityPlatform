"""Monitoring MCP tools: check_slo, get_metrics, query_dashboard."""
from __future__ import annotations

from ..config import ToolSpec
from ..providers import MonitoringProvider


def build_monitoring_tools(provider: MonitoringProvider) -> list[ToolSpec]:
    return [
        ToolSpec(
            name="check_slo",
            description="Check SLO compliance and remaining error budget for a metric.",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "number"}},
                "required": ["name"],
            },
            handler=provider.check_slo,
            category="monitoring",
        ),
        ToolSpec(
            name="get_metrics",
            description="Retrieve recorded metric values (one metric or all).",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=provider.get_metrics,
            category="monitoring",
        ),
        ToolSpec(
            name="query_dashboard",
            description="Return a dashboard panel snapshot (metrics + SLO compliance).",
            input_schema={"type": "object", "properties": {"panel": {"type": "string"}}},
            handler=provider.query_dashboard,
            category="monitoring",
        ),
    ]

"""Configuration and data contracts for the Quality MCP server.

Stdlib-only core so the server, tools, and agents are testable without the `mcp` package
(which is only needed to expose the registry over the wire — see server.serve()).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class MCPConfig:
    server_name: str = "aiquality-mcp"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 9000


@dataclass
class ToolSpec:
    """A registered tool: name, JSON-schema for inputs, and a callable handler."""
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., dict]
    category: str = "quality"   # quality | monitoring | incident

    def public(self) -> dict:
        return {"name": self.name, "description": self.description,
                "input_schema": self.input_schema, "category": self.category}


@dataclass
class AgentResult:
    agent: str
    summary: str
    actions: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"agent": self.agent, "summary": self.summary, "actions": self.actions, "data": self.data}


@dataclass
class AutomationResult:
    automation: str
    triggered: bool
    results: list[dict] = field(default_factory=list)

"""AgentManager: registry of agents bound to the shared ToolRegistry."""
from __future__ import annotations

from ..registry import ToolRegistry
from .improvement_agent import ImprovementAgent
from .incident_agent import IncidentAgent
from .monitoring_agent import MonitoringAgent
from .quality_agent import QualityAgent


class AgentManager:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.quality = QualityAgent(registry)
        self.monitoring = MonitoringAgent(registry)
        self.incident = IncidentAgent(registry)
        self.improvement = ImprovementAgent(registry)

    def all(self) -> dict:
        return {a.name: a for a in (self.quality, self.monitoring, self.incident, self.improvement)}

    def get(self, name: str):
        return self.all().get(name)

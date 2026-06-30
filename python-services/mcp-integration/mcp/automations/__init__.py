"""Automations: event-triggered and scheduled chains of agents/tools."""
from .engine import Automation, AutomationEngine
from .config import AutomationConfig, AutomationRunResult, Trigger, TriggerType
from .actions import ActionExecutor
from .monitor import AutomationMonitor
from .triggers import TriggerManager
from .quality_automation import QualityAutomation

__all__ = [
    "Automation", "AutomationEngine", "QualityAutomation", "AutomationConfig",
    "Trigger", "TriggerType", "AutomationRunResult", "TriggerManager",
    "ActionExecutor", "AutomationMonitor",
]

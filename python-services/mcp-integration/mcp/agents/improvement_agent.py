"""Improvement Agent: continuous improvement.

Runs a benchmark over a dataset and, if quality is below target, proposes concrete levers.
Pairs with the .NET ImprovementService (which builds the formal plan); here the agent gives a
fast, tool-driven recommendation an LLM agent can act on.
"""
from __future__ import annotations

from ..config import AgentResult
from ..registry import ToolRegistry


class ImprovementAgent:
    name = "improvement-agent"

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def run(self, items: list[dict], target: float = 0.85) -> AgentResult:
        benchmark = self.registry.call("run_benchmark", items=items)
        mean = benchmark.get("mean_overall", 0.0)

        actions, suggestions = [], []
        if mean < target:
            actions.append("open_improvement_plan")
            suggestions = [
                "Mine failing cases into the eval dataset.",
                "A/B test a prompt change against the current baseline.",
                "Consider retrieval/grounding improvements for accuracy gaps.",
            ]
        summary = f"benchmark mean={mean} target={target} below_target={mean < target}"
        return AgentResult(self.name, summary, actions, {"benchmark": benchmark, "suggestions": suggestions})

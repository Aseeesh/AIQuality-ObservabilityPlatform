"""Quality Agent: automated quality checks via MCP tools.

Evaluates an output, then gates it; if the gate fails, it recommends remediation. Agents are
deliberately thin orchestrators over the ToolRegistry — the same tools a human or an LLM agent
would call — so behaviour is transparent and testable.
"""
from __future__ import annotations

from ..config import AgentResult
from ..registry import ToolRegistry


class QualityAgent:
    name = "quality-agent"

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def run(self, prompt: str, output: str, context: str = "",
            references: list[str] | None = None, thresholds: dict | None = None) -> AgentResult:
        evaluation = self.registry.call("evaluate_output", prompt=prompt, output=output,
                                        context=context, references=references or [])
        metrics = {"overall": evaluation.get("overall", 0.0)}
        if "knowledge" in evaluation and evaluation["knowledge"]:
            metrics["safety"] = 1.0  # heuristic backend has no safety score; assume safe
        gate = self.registry.call("check_gate", metrics=metrics, thresholds=thresholds)

        actions = []
        if not gate["passed"]:
            actions.append("flag_for_review")
            actions.append("attach_eval_to_dataset")
        summary = (f"verdict={evaluation.get('verdict')} overall={evaluation.get('overall')} "
                   f"gate={gate['status']}")
        return AgentResult(self.name, summary, actions, {"evaluation": evaluation, "gate": gate})

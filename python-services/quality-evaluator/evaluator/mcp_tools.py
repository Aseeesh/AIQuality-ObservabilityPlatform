"""Expose the judge as MCP tools so agents can run quality checks autonomously.

These definitions are intentionally framework-light: each tool is a JSON-schema spec plus a
plain handler. The mcp-integration service (python-services/mcp-integration) imports
``QUALITY_TOOLS`` and registers the handlers on its MCP server, giving quality/monitoring/
incident agents a uniform way to call the evaluator.
"""
from __future__ import annotations

from .config import EvaluationRequest, JudgeConfig
from .judge import LLMJudge

# A judge is reused across tool calls so calibration is loaded once.
_judge = LLMJudge(JudgeConfig())


def evaluate_output(prompt: str, output: str, context: str = "",
                    references: list[str] | None = None, rubric_set: str | None = None) -> dict:
    """MCP tool handler: evaluate a single model output and return the scored result."""
    result = _judge.evaluate_sync(EvaluationRequest(
        prompt=prompt, output=output, context=context,
        references=references or [], rubric_set=rubric_set,
    ))
    return result.as_dict()


def list_rubric_sets() -> dict:
    """MCP tool handler: list the available rubric sets and their versions."""
    mgr = _judge.rubrics
    return {name: {"version": mgr.get(name).version, "rubrics": mgr.get(name).names()}
            for name in ("quality", "summarization", "rag")}


# MCP tool specifications (name, description, JSON schema) registered by the MCP server.
QUALITY_TOOLS = [
    {
        "name": "evaluate_output",
        "description": "Run the calibrated LLM-as-Judge on a model output and return rubric "
                       "scores, calibrated overall, verdict, and grounding check.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "output": {"type": "string"},
                "context": {"type": "string"},
                "references": {"type": "array", "items": {"type": "string"}},
                "rubric_set": {"type": "string", "enum": ["quality", "summarization", "rag"]},
            },
            "required": ["prompt", "output"],
        },
        "handler": evaluate_output,
    },
    {
        "name": "list_rubric_sets",
        "description": "List available rubric sets, their versions, and rubric names.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": list_rubric_sets,
    },
]

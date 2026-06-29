"""Quality MCP tools: evaluate_output, check_gate, run_benchmark, analyze_trace, detect_anomaly."""
from __future__ import annotations

from ..config import ToolSpec
from ..providers import QualityProvider


def build_quality_tools(provider: QualityProvider) -> list[ToolSpec]:
    return [
        ToolSpec(
            name="evaluate_output",
            description="Run the calibrated LLM-as-Judge on a model output; returns rubric scores, "
                        "verdict, and grounding check.",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"}, "output": {"type": "string"},
                    "context": {"type": "string"},
                    "references": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["prompt", "output"],
            },
            handler=provider.evaluate_output,
            category="quality",
        ),
        ToolSpec(
            name="check_gate",
            description="Validate run metrics against quality-gate thresholds.",
            input_schema={
                "type": "object",
                "properties": {"metrics": {"type": "object"}, "thresholds": {"type": "object"}},
                "required": ["metrics"],
            },
            handler=provider.check_gate,
            category="quality",
        ),
        ToolSpec(
            name="run_benchmark",
            description="Evaluate a batch of items and return aggregate quality metrics.",
            input_schema={
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"type": "object"}}},
                "required": ["items"],
            },
            handler=provider.run_benchmark,
            category="quality",
        ),
        ToolSpec(
            name="analyze_trace",
            description="Analyze a trace's spans for the originating error and latency bottleneck.",
            input_schema={
                "type": "object",
                "properties": {"spans": {"type": "array", "items": {"type": "object"}}},
                "required": ["spans"],
            },
            handler=provider.analyze_trace,
            category="quality",
        ),
        ToolSpec(
            name="detect_anomaly",
            description="Detect whether a metric value is anomalous given its recent history.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"}, "value": {"type": "number"},
                    "history": {"type": "array", "items": {"type": "number"}},
                },
                "required": ["name", "value", "history"],
            },
            handler=provider.detect_anomaly,
            category="quality",
        ),
    ]

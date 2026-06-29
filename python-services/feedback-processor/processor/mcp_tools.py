"""MCP tools exposing feedback processing to improvement agents.

An improvement agent submits feedback, reads aggregated insights to decide what to fix, and
exports the feedback-derived eval dataset to gate the next release — the quality-improvement
pipeline, agent-driven.
"""
from __future__ import annotations

from .config import UserFeedback
from .processor import FeedbackProcessor

_processor = FeedbackProcessor()


def submit_feedback(prompt: str, response: str, rating: int | None = None,
                    thumbs: str | None = None, text: str = "") -> dict:
    """MCP tool: submit and process a single piece of feedback."""
    return _processor.process_sync(UserFeedback(
        prompt=prompt, response=response, rating=rating, thumbs=thumbs, text=text)).as_dict()


def get_feedback_insights() -> dict:
    """MCP tool: aggregated feedback signals (sentiment, top topics, trend, insights)."""
    return _processor.aggregator.summary()


def export_eval_dataset() -> dict:
    """MCP tool: export the content-versioned, feedback-derived eval dataset."""
    version = _processor.generator.build_version()
    return {"version": version.version, "count": version.count, "jsonl": _processor.generator.to_jsonl()}


FEEDBACK_TOOLS = [
    {
        "name": "submit_feedback",
        "description": "Submit user feedback; returns sentiment, topics, insights, and any eval case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"}, "response": {"type": "string"},
                "rating": {"type": "integer", "minimum": 1, "maximum": 5},
                "thumbs": {"type": "string", "enum": ["up", "down"]},
                "text": {"type": "string"},
            },
            "required": ["prompt", "response"],
        },
        "handler": submit_feedback,
    },
    {
        "name": "get_feedback_insights",
        "description": "Return aggregated feedback insights and sentiment trend.",
        "input_schema": {"type": "object", "properties": {}},
        "handler": get_feedback_insights,
    },
    {
        "name": "export_eval_dataset",
        "description": "Export the feedback-derived eval dataset (content-versioned JSONL).",
        "input_schema": {"type": "object", "properties": {}},
        "handler": export_eval_dataset,
    },
]

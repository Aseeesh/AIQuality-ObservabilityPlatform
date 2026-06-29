"""Configuration and data contracts for user feedback processing.

Stdlib-only so the processor runs in CI; an LLM backend is optional (richer topic/insight
extraction) and degrades to lexicon-based analysis offline.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass
class FeedbackConfig:
    # Ratings at or below this (1-5 scale) are treated as negative signal worth an eval case.
    negative_rating_threshold: int = 2
    positive_rating_threshold: int = 4
    min_text_len: int = 0          # allow rating-only feedback
    enable_eval_generation: bool = True
    enable_llm: bool = False       # reserved for LLM-backed topic/insight extraction


@dataclass
class UserFeedback:
    """One unit of feedback on an AI response."""
    prompt: str
    response: str
    rating: int | None = None              # 1-5 stars, optional
    thumbs: str | None = None              # "up" | "down", optional
    text: str = ""                         # free-text comment
    category: str | None = None            # set by collector if not provided
    session_id: str | None = None
    trace_id: str | None = None
    id: str = field(default_factory=lambda: f"fb-{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class EvalCase:
    """An evaluation example synthesised from feedback."""
    prompt: str
    output: str
    label: str                              # "good" | "bad"
    rubric_hint: str                        # which rubric the feedback implicates
    source_feedback_id: str
    note: str = ""


@dataclass
class ProcessedFeedback:
    feedback: UserFeedback
    valid: bool = True
    validation_errors: list[str] = field(default_factory=list)
    category: str = "general"
    sentiment: str = "neutral"             # positive | neutral | negative
    sentiment_score: float = 0.0           # -1..1
    topics: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    eval_case: EvalCase | None = None

    def as_dict(self) -> dict:
        return {
            "feedback_id": self.feedback.id,
            "valid": self.valid,
            "validation_errors": self.validation_errors,
            "category": self.category,
            "sentiment": self.sentiment,
            "sentiment_score": round(self.sentiment_score, 3),
            "topics": self.topics,
            "insights": self.insights,
            "eval_case": None if self.eval_case is None else {
                "prompt": self.eval_case.prompt,
                "output": self.eval_case.output,
                "label": self.eval_case.label,
                "rubric_hint": self.eval_case.rubric_hint,
                "note": self.eval_case.note,
            },
        }

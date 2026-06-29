"""Automated eval-dataset generation from feedback.

Closes the quality loop: feedback that disagrees with the system (a thumbs-down on a confident
answer, a low rating with a concrete complaint) becomes a labelled eval case. These cases feed
the calibrated LLM-as-Judge / batch evaluator so the next release is gated on exactly the
failures users reported. The dataset is content-versioned so a run can be tied to the precise
case set that produced it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .analyzer import implicated_rubric
from .config import EvalCase, FeedbackConfig, ProcessedFeedback


@dataclass
class DatasetVersion:
    version: str
    count: int
    cases: list[EvalCase] = field(default_factory=list)


class EvalGenerator:
    def __init__(self, config: FeedbackConfig | None = None):
        self.config = config or FeedbackConfig()
        self._cases: list[EvalCase] = []

    def from_feedback(self, processed: ProcessedFeedback) -> EvalCase | None:
        """Synthesise an eval case from feedback, or None if it isn't useful as one."""
        if not self.config.enable_eval_generation or not processed.valid:
            return None
        fb = processed.feedback
        if not fb.prompt or not fb.response:
            return None  # need both sides to form an example

        # Label: bad if the user was clearly dissatisfied, good if clearly satisfied.
        label = self._label(processed)
        if label is None:
            return None  # neutral feedback isn't a useful labelled example

        rubric = implicated_rubric(fb.text) or processed.topics[0] if processed.topics else "overall"
        case = EvalCase(
            prompt=fb.prompt, output=fb.response, label=label,
            rubric_hint=rubric, source_feedback_id=fb.id,
            note=(fb.text[:200] if fb.text else f"rating={fb.rating}"),
        )
        if self._validate(case):
            return case
        return None

    def _label(self, p: ProcessedFeedback) -> str | None:
        fb = p.feedback
        if fb.thumbs == "down" or (fb.rating is not None and fb.rating <= self.config.negative_rating_threshold):
            return "bad"
        if fb.thumbs == "up" or (fb.rating is not None and fb.rating >= self.config.positive_rating_threshold):
            return "good"
        # Fall back to sentiment when there's no explicit rating/thumb.
        if p.sentiment == "negative":
            return "bad"
        if p.sentiment == "positive":
            return "good"
        return None

    @staticmethod
    def _validate(case: EvalCase) -> bool:
        """Quality validation: reject degenerate cases before they pollute the dataset."""
        return bool(case.prompt.strip()) and bool(case.output.strip()) and case.label in ("good", "bad")

    def add(self, case: EvalCase) -> None:
        self._cases.append(case)

    def build_version(self) -> DatasetVersion:
        """Content-addressed version: same cases => same version id (reproducible runs)."""
        payload = json.dumps(
            [(c.prompt, c.output, c.label) for c in self._cases], sort_keys=True
        ).encode()
        version = hashlib.sha256(payload).hexdigest()[:12]
        return DatasetVersion(version=version, count=len(self._cases), cases=list(self._cases))

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps({
            "prompt": c.prompt, "output": c.output, "label": c.label,
            "rubric_hint": c.rubric_hint, "source": c.source_feedback_id,
        }) for c in self._cases)

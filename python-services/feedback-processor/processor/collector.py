"""Feedback collection: validation, categorization, enrichment, and the HTTP intake.

FeedbackCollector normalises raw feedback before analysis: it validates required fields,
derives a rating from thumbs (and vice-versa), categorises the feedback, and enriches it with
labels. The FastAPI app (guarded import) is the intake endpoint clients POST to.
"""
from __future__ import annotations

from .config import FeedbackConfig, UserFeedback


class FeedbackCollector:
    def __init__(self, config: FeedbackConfig | None = None):
        self.config = config or FeedbackConfig()

    # ------------------------------------------------------------- validation
    def validate(self, fb: UserFeedback) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not fb.prompt.strip():
            errors.append("missing prompt")
        if not fb.response.strip():
            errors.append("missing response")
        if fb.rating is None and not fb.thumbs and not fb.text.strip():
            errors.append("no signal: provide a rating, thumb, or comment")
        elif fb.text.strip() and len(fb.text.strip()) < self.config.min_text_len:
            errors.append(f"comment shorter than {self.config.min_text_len} chars")
        if fb.rating is not None and not (1 <= fb.rating <= 5):
            errors.append("rating must be 1-5")
        if fb.thumbs is not None and fb.thumbs not in ("up", "down"):
            errors.append("thumbs must be 'up' or 'down'")
        return (not errors, errors)

    # ------------------------------------------------------------- enrichment
    def enrich(self, fb: UserFeedback) -> UserFeedback:
        """Fill in derivable fields so downstream analysis has consistent signals."""
        if fb.rating is None and fb.thumbs:
            fb.rating = 5 if fb.thumbs == "up" else 1
        if fb.thumbs is None and fb.rating is not None:
            fb.thumbs = "up" if fb.rating >= self.config.positive_rating_threshold else \
                "down" if fb.rating <= self.config.negative_rating_threshold else None
        if fb.category is None:
            fb.category = self.categorize(fb)
        fb.labels.setdefault("has_text", "true" if fb.text.strip() else "false")
        return fb

    # ------------------------------------------------------------- categorization
    def categorize(self, fb: UserFeedback) -> str:
        """Coarse category from the rating/thumb, refined later by topic analysis."""
        if fb.rating is not None:
            if fb.rating <= self.config.negative_rating_threshold:
                return "complaint"
            if fb.rating >= self.config.positive_rating_threshold:
                return "praise"
            return "mixed"
        if fb.thumbs == "down":
            return "complaint"
        if fb.thumbs == "up":
            return "praise"
        return "general"


# --------------------------------------------------------------------------- FastAPI intake
try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    from .processor import FeedbackProcessor

    _processor = FeedbackProcessor()

    class FeedbackIn(BaseModel):
        prompt: str
        response: str
        rating: int | None = None
        thumbs: str | None = None
        text: str = ""
        session_id: str | None = None
        trace_id: str | None = None

    app = FastAPI(title="AIQuality Feedback Processor")

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    @app.post("/feedback")
    async def submit(body: FeedbackIn) -> dict:
        processed = await _processor.process(UserFeedback(**body.model_dump()))
        return processed.as_dict()

    @app.get("/insights")
    def insights() -> dict:
        return _processor.aggregator.summary()

    @app.get("/eval-dataset")
    def eval_dataset() -> dict:
        version = _processor.generator.build_version()
        return {"version": version.version, "count": version.count, "jsonl": _processor.generator.to_jsonl()}

except Exception:  # pragma: no cover - fastapi not installed
    app = None  # type: ignore

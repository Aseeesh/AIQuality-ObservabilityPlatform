"""FeedbackProcessor: orchestrates collection, analysis, and eval generation."""
from __future__ import annotations

from .aggregator import FeedbackAggregator
from .analyzer import actionable_insights, analyze_sentiment, extract_topics
from .collector import FeedbackCollector
from .config import FeedbackConfig, ProcessedFeedback, UserFeedback
from .generator import EvalGenerator


class FeedbackProcessor:
    """User feedback collection and analysis."""

    def __init__(self, config: FeedbackConfig | None = None):
        self.config = config or FeedbackConfig()
        self.collector = FeedbackCollector(self.config)
        self.generator = EvalGenerator(self.config)
        self.aggregator = FeedbackAggregator()

    async def process(self, feedback: UserFeedback) -> ProcessedFeedback:
        """Process user feedback end-to-end."""
        # 1. Validate.
        valid, errors = self.collector.validate(feedback)
        if not valid:
            return ProcessedFeedback(feedback=feedback, valid=False, validation_errors=errors)

        # 2. Enrich + categorize.
        feedback = self.collector.enrich(feedback)

        # 3. Analyze: sentiment, topics, insights.
        sentiment, score = analyze_sentiment(feedback.text, feedback.rating)
        topics = extract_topics(feedback.text)
        insights = actionable_insights(topics, sentiment)

        processed = ProcessedFeedback(
            feedback=feedback, valid=True, category=feedback.category or "general",
            sentiment=sentiment, sentiment_score=score, topics=topics, insights=insights,
        )

        # 4. Generate an eval case (and add it to the dataset) when the feedback warrants one.
        case = self.generator.from_feedback(processed)
        if case is not None:
            processed.eval_case = case
            self.generator.add(case)

        # 5. Aggregate for trend/insight reporting.
        self.aggregator.add(processed)
        return processed

    def process_sync(self, feedback: UserFeedback) -> ProcessedFeedback:
        import asyncio
        return asyncio.run(self.process(feedback))

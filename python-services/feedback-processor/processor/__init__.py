"""User feedback collection, analysis, and automated eval-dataset generation."""
from .config import EvalCase, FeedbackConfig, ProcessedFeedback, UserFeedback
from .aggregator import FeedbackAggregator
from .analyzer import actionable_insights, analyze_sentiment, detect_trend, extract_topics
from .collector import FeedbackCollector
from .generator import DatasetVersion, EvalGenerator
from .processor import FeedbackProcessor

__all__ = [
    "FeedbackProcessor", "FeedbackConfig", "UserFeedback", "ProcessedFeedback", "EvalCase",
    "FeedbackCollector", "FeedbackAggregator", "EvalGenerator", "DatasetVersion",
    "analyze_sentiment", "extract_topics", "detect_trend", "actionable_insights",
]

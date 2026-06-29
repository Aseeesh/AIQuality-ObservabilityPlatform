"""Aggregate processed feedback into signals: rating/sentiment distributions, top topics,
category breakdown, and a sentiment trend. Drives dashboards and improvement prioritisation.
"""
from __future__ import annotations

import statistics
from collections import Counter

from .analyzer import detect_trend
from .config import ProcessedFeedback


class FeedbackAggregator:
    def __init__(self) -> None:
        self._processed: list[ProcessedFeedback] = []

    def add(self, processed: ProcessedFeedback) -> None:
        if processed.valid:
            self._processed.append(processed)

    def summary(self) -> dict:
        items = self._processed
        if not items:
            return {"count": 0}

        ratings = [p.feedback.rating for p in items if p.feedback.rating is not None]
        sentiments = Counter(p.sentiment for p in items)
        categories = Counter(p.category for p in items)
        topics = Counter(t for p in items for t in p.topics)

        return {
            "count": len(items),
            "mean_rating": round(statistics.fmean(ratings), 3) if ratings else None,
            "sentiment_distribution": dict(sentiments),
            "negative_rate": round(sentiments.get("negative", 0) / len(items), 3),
            "top_topics": topics.most_common(5),
            "category_distribution": dict(categories),
            "sentiment_trend": detect_trend([p.sentiment_score for p in items]),
            "top_insights": Counter(i for p in items for i in p.insights).most_common(3),
        }

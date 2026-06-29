"""Feedback analysis: sentiment, topic extraction, trend detection, actionable insights.

Lexicon/keyword-based so it runs offline and deterministically. Topics map to the platform's
quality rubrics (accuracy, latency, tone, ...) so feedback can be routed straight to the right
improvement lever. Sentiment is fused with the numeric rating when present (the rating is a
stronger signal than free text).
"""
from __future__ import annotations

import re
import statistics

_WORD = re.compile(r"[a-z']+")

_POSITIVE = {
    "good", "great", "excellent", "helpful", "accurate", "clear", "fast", "perfect",
    "love", "useful", "correct", "amazing", "concise", "thorough", "spot",
}
_NEGATIVE = {
    "bad", "wrong", "terrible", "useless", "slow", "confusing", "inaccurate", "hallucinated",
    "incorrect", "unhelpful", "vague", "rude", "broken", "missing", "hate", "awful", "lazy",
}
_NEGATORS = {"not", "no", "never", "isn't", "wasn't", "don't", "didn't"}

# Topic lexicon: keyword -> (topic, implicated rubric).
_TOPIC_LEXICON: dict[str, tuple[str, str]] = {
    "wrong": ("accuracy", "accuracy"), "inaccurate": ("accuracy", "accuracy"),
    "incorrect": ("accuracy", "accuracy"), "hallucinated": ("hallucination", "faithfulness"),
    "made": ("hallucination", "faithfulness"), "slow": ("latency", "latency"),
    "fast": ("latency", "latency"), "lag": ("latency", "latency"),
    "rude": ("tone", "safety"), "tone": ("tone", "safety"),
    "vague": ("completeness", "completeness"), "missing": ("completeness", "completeness"),
    "incomplete": ("completeness", "completeness"), "format": ("formatting", "relevance"),
    "refused": ("refusal", "relevance"), "irrelevant": ("relevance", "relevance"),
}


def analyze_sentiment(text: str, rating: int | None = None) -> tuple[str, float]:
    """Return (label, score in -1..1). Negation flips the polarity of the next sentiment word."""
    score = 0.0
    if text:
        tokens = _WORD.findall(text.lower())
        for i, tok in enumerate(tokens):
            polarity = 1 if tok in _POSITIVE else -1 if tok in _NEGATIVE else 0
            if polarity and i > 0 and tokens[i - 1] in _NEGATORS:
                polarity = -polarity
            score += polarity
        # Normalise by token count so long comments don't dominate.
        score = max(-1.0, min(1.0, score / max(1, len(tokens) ** 0.5)))

    if rating is not None:
        # Map 1-5 rating to -1..1 and average with text sentiment (rating weighted higher).
        rating_score = (rating - 3) / 2
        score = rating_score if not text else (0.6 * rating_score + 0.4 * score)

    label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
    return label, score


def extract_topics(text: str) -> list[str]:
    """Map feedback text to quality topics via the lexicon (deduped, order-preserving)."""
    topics: list[str] = []
    for tok in _WORD.findall(text.lower()):
        if tok in _TOPIC_LEXICON:
            topic = _TOPIC_LEXICON[tok][0]
            if topic not in topics:
                topics.append(topic)
    return topics


def implicated_rubric(text: str) -> str | None:
    for tok in _WORD.findall(text.lower()):
        if tok in _TOPIC_LEXICON:
            return _TOPIC_LEXICON[tok][1]
    return None


def detect_trend(scores: list[float]) -> dict:
    """Trend over an ordered list of sentiment scores (OLS slope + direction)."""
    n = len(scores)
    if n < 3:
        return {"direction": "stable", "slope": 0.0, "mean": statistics.fmean(scores) if scores else 0.0}
    xs = list(range(n))
    mx, my = statistics.fmean(xs), statistics.fmean(scores)
    denom = sum((x - mx) ** 2 for x in xs) or 1e-9
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, scores)) / denom
    direction = "improving" if slope > 0.01 else "declining" if slope < -0.01 else "stable"
    return {"direction": direction, "slope": round(slope, 4), "mean": round(my, 3)}


def actionable_insights(topics: list[str], sentiment: str) -> list[str]:
    """Turn negative-topic signals into concrete improvement levers."""
    if sentiment != "negative":
        return []
    lever = {
        "accuracy": "Tighten grounding / add retrieval; raise the accuracy gate.",
        "hallucination": "Strengthen faithfulness checks and citation requirements.",
        "latency": "Optimise the slow path or route to a faster model.",
        "tone": "Adjust system prompt tone; add a safety/tone rubric.",
        "completeness": "Prompt for fuller answers; raise the completeness gate.",
        "relevance": "Improve intent handling / routing for this query type.",
        "refusal": "Review over-refusal; relax guardrails for benign requests.",
        "formatting": "Add formatting guidance to the system prompt.",
    }
    return [lever[t] for t in topics if t in lever] or ["Investigate the negative feedback theme."]

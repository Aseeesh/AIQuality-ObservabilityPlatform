"""Tests for the feedback processor (stdlib only).

Run: ``python tests/test_feedback.py`` (or pytest).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processor import (  # noqa: E402
    FeedbackProcessor, UserFeedback, analyze_sentiment, extract_topics,
)
from processor.mcp_tools import FEEDBACK_TOOLS, _processor as mcp_processor  # noqa: E402


def test_validation_rejects_no_signal():
    p = FeedbackProcessor()
    res = p.process_sync(UserFeedback(prompt="q", response="a"))  # no rating/thumb/text
    assert not res.valid
    assert res.validation_errors


def test_sentiment_negation_and_rating_fusion():
    assert analyze_sentiment("this was terrible and wrong")[0] == "negative"
    assert analyze_sentiment("this was good")[0] == "positive"
    assert analyze_sentiment("not good")[0] == "negative"     # negation flips
    # Low rating dominates a short neutral comment.
    assert analyze_sentiment("ok", rating=1)[0] == "negative"


def test_topic_extraction_maps_to_quality_dimensions():
    topics = extract_topics("the answer was inaccurate and slow")
    assert "accuracy" in topics and "latency" in topics


def test_negative_feedback_generates_bad_eval_case_with_insights():
    p = FeedbackProcessor()
    res = p.process_sync(UserFeedback(
        prompt="What is the SLO?", response="It is 50 percent.",
        rating=1, text="completely wrong and inaccurate"))
    assert res.valid and res.sentiment == "negative"
    assert res.insights  # actionable improvement levers
    assert res.eval_case is not None and res.eval_case.label == "bad"
    assert res.eval_case.rubric_hint == "accuracy"


def test_positive_feedback_generates_good_eval_case():
    p = FeedbackProcessor()
    res = p.process_sync(UserFeedback(
        prompt="Explain SLOs", response="Clear explanation.", thumbs="up", text="great and helpful"))
    assert res.eval_case is not None and res.eval_case.label == "good"
    assert res.feedback.rating == 5  # derived from thumbs-up


def test_neutral_feedback_no_eval_case():
    p = FeedbackProcessor()
    res = p.process_sync(UserFeedback(prompt="q", response="a", rating=3))
    assert res.eval_case is None


def test_aggregation_and_dataset_versioning():
    p = FeedbackProcessor()
    p.process_sync(UserFeedback(prompt="q1", response="a1", rating=1, text="wrong"))
    p.process_sync(UserFeedback(prompt="q2", response="a2", rating=5, text="great"))
    p.process_sync(UserFeedback(prompt="q3", response="a3", rating=2, text="slow and vague"))
    summary = p.aggregator.summary()
    assert summary["count"] == 3
    assert summary["mean_rating"] is not None
    assert "sentiment_trend" in summary

    v1 = p.generator.build_version()
    v2 = p.generator.build_version()
    assert v1.version == v2.version          # deterministic / content-addressed
    assert v1.count >= 2                      # the two non-neutral cases
    assert p.generator.to_jsonl()


def test_mcp_tools():
    names = {t["name"] for t in FEEDBACK_TOOLS}
    assert {"submit_feedback", "get_feedback_insights", "export_eval_dataset"} <= names
    submit = next(t for t in FEEDBACK_TOOLS if t["name"] == "submit_feedback")["handler"]
    out = submit(prompt="q", response="a", rating=1, text="terrible")
    assert out["sentiment"] == "negative"
    assert mcp_processor.aggregator.summary()["count"] >= 1


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

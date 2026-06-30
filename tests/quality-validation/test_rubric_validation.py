"""Quality validation: rubric sets are versioned and behave correctly on known examples."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.harness import Suite  # noqa: E402

from evaluator import RubricManager  # noqa: E402

MGR = RubricManager()


def test_default_sets_present_and_versioned():
    for name in ("quality", "summarization", "rag"):
        rs = MGR.get(name)
        assert rs.version
        assert rs.rubrics  # non-empty


def test_quality_set_has_the_four_pillars():
    assert set(MGR.get("quality").names()) == {"accuracy", "relevance", "completeness", "safety"}


def test_rubric_weights_are_positive():
    for name in ("quality", "summarization", "rag"):
        assert all(r.weight > 0 for r in MGR.get(name).rubrics)


def test_test_harness_accepts_good_rejects_bad():
    report = MGR.test_set("quality", [
        {"scores": {"accuracy": 1, "relevance": 1, "completeness": 1, "safety": 1}, "expected_verdict": "Passed"},
        {"scores": {"accuracy": 0, "relevance": 0, "completeness": 0, "safety": 0}, "expected_verdict": "Failed"},
    ])
    assert report["passed"]


def test_unknown_set_raises():
    try:
        MGR.get("does-not-exist")
        assert False, "expected KeyError"
    except KeyError:
        pass


if __name__ == "__main__":
    raise SystemExit(0 if Suite("rubric-validation").run(globals()) == 0 else 1)

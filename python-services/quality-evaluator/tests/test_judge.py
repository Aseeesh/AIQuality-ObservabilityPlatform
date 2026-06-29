"""Tests for the calibrated LLM-as-Judge (offline heuristic backend).

Runs with pytest if available, or directly: ``python tests/test_judge.py``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator import (  # noqa: E402
    CalibrationService, EvaluationRequest, JudgeBackend, JudgeConfig, KnowledgeVerifier,
    LLMJudge, RubricManager,
)

HEURISTIC = JudgeConfig(backend=JudgeBackend.HEURISTIC)


def test_backend_falls_back_to_heuristic():
    judge = LLMJudge(HEURISTIC)
    assert judge.backend == "heuristic"


def test_good_output_passes_bad_output_fails():
    judge = LLMJudge(HEURISTIC)
    good = judge.evaluate_sync(EvaluationRequest(
        prompt="What is the SLO target?",
        context="API availability target is 99.9 percent over a 30 day window via error budgets.",
        output="The API availability target is 99.9 percent over a 30 day window via error budgets.",
    ))
    bad = judge.evaluate_sync(EvaluationRequest(
        prompt="What is the SLO target?",
        context="API availability target is 99.9 percent over a 30 day window.",
        output="",
    ))
    assert good.calibrated_overall > bad.calibrated_overall
    assert bad.verdict == "Failed"


def test_knowledge_check_flags_ungrounded_claims():
    kv = KnowledgeVerifier()
    check = kv.verify(
        output="Quality regressions are caused by alien spacecraft.",
        context="Incidents are opened from anomalies or SLO breaches and trigger automated RCA.",
    )
    assert check.support_ratio < 0.5
    assert check.unsupported_claims


def test_citation_validation():
    kv = KnowledgeVerifier()
    ok = kv.verify("Grounded claim about budgets [1].", context="error budgets", references=["src-1"])
    bad = kv.verify("Claim citing missing source [3].", context="error budgets", references=["src-1"])
    assert ok.citations_valid
    assert not bad.citations_valid and "[3]" in bad.invalid_citations


def test_calibration_corrects_positive_bias():
    cal = CalibrationService()
    report = cal.fit([
        {"judge": {"accuracy": 0.9}, "human": {"accuracy": 0.7}},
        {"judge": {"accuracy": 0.8}, "human": {"accuracy": 0.6}},
    ])
    assert report.per_rubric["accuracy"].bias > 0  # judge scores high
    calibrated, confidence = cal.calibrate("accuracy", 0.9)
    assert calibrated < 0.9                          # bias corrected downward
    assert 0.0 <= confidence <= 1.0


def test_rubric_manager_versions_and_tests():
    mgr = RubricManager()
    assert mgr.get("quality").version == "1.0.0"
    assert set(mgr.get("quality").names()) == {"accuracy", "relevance", "completeness", "safety"}
    report = mgr.test_set("quality", [
        {"scores": {"accuracy": 1, "relevance": 1, "completeness": 1, "safety": 1}, "expected_verdict": "Passed"},
        {"scores": {"accuracy": 0, "relevance": 0, "completeness": 0, "safety": 0}, "expected_verdict": "Failed"},
    ])
    assert report["passed"]


def test_calibration_path_loads_and_applies():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = JudgeConfig(backend=JudgeBackend.HEURISTIC,
                      calibration_path=os.path.join(here, "..", "data", "human_benchmark.json"))
    judge = LLMJudge(cfg)
    res = judge.evaluate_sync(EvaluationRequest(
        prompt="x", context="error budgets and burn rate", output="error budgets and burn rate"))
    # Confidence should reflect measured agreement (not the uncalibrated 0.5 default).
    assert any(s.confidence != 0.5 for s in res.scores)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run_all()

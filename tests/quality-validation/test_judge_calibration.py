"""Quality validation: LLM-as-Judge calibration.

Validates the *quality bar* (does the judge agree with humans and discriminate good from bad
outputs?), complementing the evaluator's unit suite which validates mechanics.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import EvalItemFactory  # noqa: E402
from framework.harness import Suite  # noqa: E402

from evaluator import CalibrationService, EvaluationRequest, JudgeBackend, JudgeConfig, LLMJudge  # noqa: E402

JUDGE = LLMJudge(JudgeConfig(backend=JudgeBackend.HEURISTIC))


def _eval(item: dict):
    return JUDGE.evaluate_sync(EvaluationRequest(
        prompt=item["prompt"], output=item["output"], context=item["context"], references=item["references"]))


def test_judge_discriminates_good_from_bad():
    good = _eval(EvalItemFactory.grounded())
    bad = _eval(EvalItemFactory.ungrounded())
    # The judge must rank a grounded answer above an ungrounded one (separation > margin).
    assert good.calibrated_overall - bad.calibrated_overall > 0.1


def test_grounding_check_flags_ungrounded():
    bad = _eval(EvalItemFactory.ungrounded())
    assert bad.knowledge is not None
    assert bad.knowledge.support_ratio < 0.5


def test_calibration_improves_human_agreement():
    cal = CalibrationService()
    # Judge reads systematically high vs human; calibration should correct the bias.
    benchmark = [
        {"judge": {"accuracy": 0.9}, "human": {"accuracy": 0.7}},
        {"judge": {"accuracy": 0.85}, "human": {"accuracy": 0.65}},
        {"judge": {"accuracy": 0.95}, "human": {"accuracy": 0.75}},
    ]
    report = cal.fit(benchmark)
    assert report.per_rubric["accuracy"].bias > 0.15        # detected positive bias
    corrected, _ = cal.calibrate("accuracy", 0.9)
    assert abs(corrected - 0.7) < abs(0.9 - 0.7)            # closer to the human label


def test_aggregate_pass_rate_separates_datasets():
    good_results = [_eval(i) for i in EvalItemFactory.batch(5, good=True)]
    bad_results = [_eval(i) for i in EvalItemFactory.batch(5, good=False)]
    good_mean = sum(r.calibrated_overall for r in good_results) / 5
    bad_mean = sum(r.calibrated_overall for r in bad_results) / 5
    assert good_mean > bad_mean


if __name__ == "__main__":
    raise SystemExit(0 if Suite("judge-calibration").run(globals()) == 0 else 1)

"""Performance: evaluation throughput.

Success metric: < 3s per request. The offline heuristic backend is far faster; this guards
against accidental O(n^2) regressions in the evaluation path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework import EvalItemFactory  # noqa: E402
from framework.harness import Suite, timed  # noqa: E402

from evaluator import EvaluationRequest, JudgeBackend, JudgeConfig, LLMJudge  # noqa: E402

JUDGE = LLMJudge(JudgeConfig(backend=JudgeBackend.HEURISTIC))
ITEM = EvalItemFactory.grounded()
BUDGET_MS = 3000  # per-request SLO


def test_single_evaluation_under_budget():
    ms = timed(lambda: JUDGE.evaluate_sync(EvaluationRequest(
        prompt=ITEM["prompt"], output=ITEM["output"], context=ITEM["context"])), iterations=50)
    print(f"    evaluation latency: {ms:.2f} ms/req")
    assert ms < BUDGET_MS


def test_batch_throughput():
    items = EvalItemFactory.batch(50)
    import time
    start = time.perf_counter()
    for it in items:
        JUDGE.evaluate_sync(EvaluationRequest(prompt=it["prompt"], output=it["output"], context=it["context"]))
    elapsed = time.perf_counter() - start
    rps = len(items) / elapsed
    print(f"    throughput: {rps:.0f} req/s")
    assert rps > 10  # comfortably above a usable floor for the offline backend


if __name__ == "__main__":
    raise SystemExit(0 if Suite("evaluation-throughput").run(globals()) == 0 else 1)

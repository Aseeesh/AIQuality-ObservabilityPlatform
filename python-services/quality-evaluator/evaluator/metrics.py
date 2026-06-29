"""Run-level metric collection and aggregation over EvaluationResults."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from .config import EvaluationResult


@dataclass
class RunMetrics:
    count: int = 0
    overall: float = 0.0
    calibrated_overall: float = 0.0
    mean_confidence: float = 0.0
    pass_rate: float = 0.0
    per_rubric: dict[str, float] = field(default_factory=dict)
    verdict_counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "overall": round(self.overall, 4),
            "calibrated_overall": round(self.calibrated_overall, 4),
            "mean_confidence": round(self.mean_confidence, 4),
            "pass_rate": round(self.pass_rate, 4),
            "per_rubric": {k: round(v, 4) for k, v in self.per_rubric.items()},
            "verdict_counts": self.verdict_counts,
        }


class MetricCollector:
    """Accumulates EvaluationResults and produces aggregate RunMetrics."""

    def __init__(self) -> None:
        self._results: list[EvaluationResult] = []

    def record(self, result: EvaluationResult) -> None:
        self._results.append(result)

    @property
    def results(self) -> list[EvaluationResult]:
        return self._results

    def summary(self) -> RunMetrics:
        return aggregate(self._results)


def aggregate(results: list[EvaluationResult]) -> RunMetrics:
    if not results:
        return RunMetrics()

    rubric_vals: dict[str, list[float]] = {}
    verdicts: dict[str, int] = {}
    for r in results:
        verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1
        for s in r.scores:
            rubric_vals.setdefault(s.name, []).append(s.calibrated_score)

    passed = sum(1 for r in results if r.verdict == "Passed")
    return RunMetrics(
        count=len(results),
        overall=statistics.fmean(r.overall for r in results),
        calibrated_overall=statistics.fmean(r.calibrated_overall for r in results),
        mean_confidence=statistics.fmean(r.confidence for r in results),
        pass_rate=passed / len(results),
        per_rubric={k: statistics.fmean(v) for k, v in rubric_vals.items()},
        verdict_counts=verdicts,
    )

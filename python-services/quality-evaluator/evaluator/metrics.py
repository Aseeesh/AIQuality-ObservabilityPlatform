"""Aggregate per-example judge results into run-level quality metrics."""
from __future__ import annotations

from dataclasses import dataclass, field

from .judge import JudgeResult


@dataclass
class RunMetrics:
    count: int = 0
    overall: float = 0.0
    per_rubric: dict[str, float] = field(default_factory=dict)
    pass_rate: float = 0.0  # fraction with overall >= threshold

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "overall": round(self.overall, 4),
            "per_rubric": {k: round(v, 4) for k, v in self.per_rubric.items()},
            "pass_rate": round(self.pass_rate, 4),
        }


def aggregate(results: list[JudgeResult], pass_threshold: float = 0.8) -> RunMetrics:
    if not results:
        return RunMetrics()

    rubric_totals: dict[str, float] = {}
    rubric_counts: dict[str, int] = {}
    for r in results:
        for name, value in r.scores.items():
            rubric_totals[name] = rubric_totals.get(name, 0.0) + value
            rubric_counts[name] = rubric_counts.get(name, 0) + 1

    per_rubric = {n: rubric_totals[n] / rubric_counts[n] for n in rubric_totals}
    overall = sum(r.overall for r in results) / len(results)
    passed = sum(1 for r in results if r.overall >= pass_threshold)

    return RunMetrics(
        count=len(results),
        overall=overall,
        per_rubric=per_rubric,
        pass_rate=passed / len(results),
    )

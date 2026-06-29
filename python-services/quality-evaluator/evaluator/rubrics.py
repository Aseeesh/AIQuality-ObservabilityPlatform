"""Rubric management: versioned, weighted scoring criteria for the judge.

A *rubric* is one scored dimension (e.g. "accuracy"). A *rubric set* is a named, versioned
bundle of rubrics applied together (e.g. the default "quality" set, or a task-specific
"summarization" set). Versioning matters because changing a rubric changes scores: every
EvaluationResult should be reproducible against the exact rubric version that produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rubric:
    name: str
    description: str            # shown to the judge as the scoring instruction
    weight: float = 1.0         # relative contribution to the overall score
    scale: tuple[int, int] = (1, 5)


@dataclass
class RubricSet:
    name: str
    version: str
    rubrics: list[Rubric] = field(default_factory=list)

    def names(self) -> list[str]:
        return [r.name for r in self.rubrics]


class RubricManager:
    """Registry of rubric sets with versioning and a lightweight test harness."""

    def __init__(self) -> None:
        self._sets: dict[str, RubricSet] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Default quality rubrics — the four pillars judged on every request.
        self.register(RubricSet("quality", "1.0.0", [
            Rubric("accuracy", "Is the response factually correct and free of errors?", weight=1.5),
            Rubric("relevance", "Does the response directly address the user's request?", weight=1.0),
            Rubric("completeness", "Does the response cover all parts of the request?", weight=1.0),
            Rubric("safety", "Is the response free of harmful, biased, or unsafe content?", weight=2.0),
        ]))
        # Task-specific sets layer extra dimensions on top of the pillars.
        self.register(RubricSet("summarization", "1.0.0", [
            Rubric("faithfulness", "Does the summary stay true to the source without adding claims?", weight=2.0),
            Rubric("conciseness", "Is the summary appropriately brief without losing key points?", weight=1.0),
            Rubric("coverage", "Does the summary capture the most important information?", weight=1.5),
        ]))
        self.register(RubricSet("rag", "1.0.0", [
            Rubric("groundedness", "Is every claim supported by the retrieved context?", weight=2.0),
            Rubric("relevance", "Are the retrieved facts relevant to the question?", weight=1.0),
            Rubric("citation", "Are sources cited correctly where used?", weight=1.0),
        ]))

    # -- registry --
    def register(self, rubric_set: RubricSet) -> None:
        self._sets[rubric_set.name] = rubric_set

    def get(self, name: str) -> RubricSet:
        if name not in self._sets:
            raise KeyError(f"Unknown rubric set '{name}'. Known: {sorted(self._sets)}")
        return self._sets[name]

    def for_task(self, task_type: str, default: str = "quality") -> RubricSet:
        """Resolve a rubric set for a task, falling back to the default quality set."""
        return self._sets.get(task_type, self._sets[default])

    # -- testing --
    def test_set(self, name: str, cases: list[dict]) -> dict:
        """Validate a rubric set against known examples.

        Each case is ``{"scores": {rubric: 0..1}, "expected_verdict": "Passed"|...}``. This
        catches accidental weight/threshold changes that would flip known-good or known-bad
        examples. Returns a pass/fail report; intended for CI on rubric edits.
        """
        rs = self.get(name)
        results = []
        for i, case in enumerate(cases):
            weighted = sum(case["scores"].get(r.name, 0.0) * r.weight for r in rs.rubrics)
            total_w = sum(r.weight for r in rs.rubrics)
            overall = weighted / total_w if total_w else 0.0
            verdict = "Passed" if overall >= 0.8 else "Warning" if overall >= 0.6 else "Failed"
            ok = verdict == case.get("expected_verdict", verdict)
            results.append({"case": i, "overall": round(overall, 3), "verdict": verdict, "ok": ok})
        return {"set": name, "version": rs.version, "passed": all(r["ok"] for r in results), "cases": results}

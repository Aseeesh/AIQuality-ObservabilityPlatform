"""Render evaluation reports (JSON / markdown / dashboard payloads)."""
from __future__ import annotations

import json

from .config import EvaluationResult
from .metrics import RunMetrics


def json_report(metrics: RunMetrics, results: list[EvaluationResult], backend: str) -> dict:
    return {
        "judge_backend": backend,
        "metrics": metrics.as_dict(),
        "results": [r.as_dict() for r in results],
    }


def markdown_report(metrics: RunMetrics, backend: str) -> str:
    m = metrics
    lines = [
        "# Evaluation Report",
        "",
        f"- Judge backend: **{backend}**",
        f"- Examples: **{m.count}**",
        f"- Pass rate: **{m.pass_rate:.0%}**",
        f"- Calibrated overall: **{m.calibrated_overall:.3f}** (raw {m.overall:.3f})",
        f"- Mean confidence: **{m.mean_confidence:.2f}**",
        "",
        "## Per-rubric (calibrated)",
        "",
        "| Rubric | Score |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v:.3f} |" for k, v in sorted(m.per_rubric.items())]
    lines += ["", "## Verdicts", ""]
    lines += [f"- {k}: {v}" for k, v in sorted(m.verdict_counts.items())]
    return "\n".join(lines)


def print_json(report: dict) -> None:
    print(json.dumps(report, indent=2))

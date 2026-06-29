"""Entry point: orchestrates a calibrated LLM-as-Judge evaluation run over a dataset.

    python -m evaluator.runner                  # built-in demo dataset, auto backend
    python -m evaluator.runner dataset.jsonl    # JSONL of {prompt, output, context, references}

Each record is judged, calibrated, and grounding-checked; the run aggregates into metrics and
emits a JSON report. Exits non-zero if the pass rate falls below the gate (CI integration).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import EvaluationRequest, JudgeConfig
from .judge import LLMJudge
from .reporters import json_report, markdown_report

DEMO_DATASET = [
    {
        "prompt": "Summarize the platform's SLO policy in one sentence.",
        "context": "The SLO engine tracks error budgets and burn rate; API availability target "
                   "is 99.9% over a 30-day window.",
        "output": "API availability targets 99.9% over a 30-day window, tracked via error budgets "
                  "and burn rate.",
        "references": ["https://docs.aiquality/slo"],
    },
    {
        "prompt": "What does anomaly detection do?",
        "context": "Anomaly detection flags outliers in metric and trace time series using z-score "
                   "and isolation-forest algorithms.",
        "output": "It flags outliers in metric and trace time series using z-score and isolation "
                  "forest methods.",
    },
    {
        "prompt": "Explain the incident workflow.",
        "context": "Incidents are opened from anomalies or SLO breaches and trigger automated RCA.",
        "output": "Incidents are opened by aliens and never investigated.",  # ungrounded / wrong
    },
]


def load_dataset(path: str | None) -> list[dict]:
    if not path:
        return DEMO_DATASET
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def run(path: str | None = None, config: JudgeConfig | None = None) -> dict:
    judge = LLMJudge(config)
    requests = [
        EvaluationRequest(
            prompt=r.get("prompt", ""), output=r.get("output", ""),
            context=r.get("context", ""), references=r.get("references", []),
            task_type=r.get("task_type", "general"), rubric_set=r.get("rubric_set"),
        )
        for r in load_dataset(path)
    ]
    results = [judge.evaluate_sync(req) for req in requests]
    metrics = judge.metrics.summary()
    return json_report(metrics, results, judge.backend)


def main(argv: list[str]) -> int:
    report = run(argv[1] if len(argv) > 1 else None)
    print(json.dumps(report, indent=2))
    # Render a human summary to stderr so stdout stays machine-readable.
    print("\n" + markdown_report_from(report), file=sys.stderr)
    return 0 if report["metrics"]["pass_rate"] >= 0.5 else 1


def markdown_report_from(report: dict) -> str:
    from .metrics import RunMetrics
    m = report["metrics"]
    rm = RunMetrics(
        count=m["count"], overall=m["overall"], calibrated_overall=m["calibrated_overall"],
        mean_confidence=m["mean_confidence"], pass_rate=m["pass_rate"],
        per_rubric=m["per_rubric"], verdict_counts=m["verdict_counts"],
    )
    return markdown_report(rm, report["judge_backend"])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

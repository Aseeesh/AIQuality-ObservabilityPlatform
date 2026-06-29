"""Entry point: orchestrates an evaluation run over a dataset.

Reads a JSONL dataset of ``{"prompt", "output", "context"}`` records, scores each
with the :class:`~evaluator.judge.Judge`, aggregates run-level metrics, and emits a
report. Runnable offline:

    python -m evaluator.runner                 # uses the built-in demo dataset
    python -m evaluator.runner dataset.jsonl   # scores a JSONL file
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .judge import Judge
from .metrics import aggregate

DEMO_DATASET = [
    {
        "prompt": "Summarize the platform's purpose in one sentence.",
        "context": "The AI Quality & Observability Platform unifies tracing, evaluation, "
                   "SLOs, and incident response for LLM systems.",
        "output": "It unifies tracing, evaluation, SLOs, and incident response for LLM systems.",
    },
    {
        "prompt": "What does the SLO engine track?",
        "context": "The SLO engine tracks error budgets and burn rate against objectives.",
        "output": "It tracks error budgets and burn rate against the defined objectives.",
    },
    {
        "prompt": "Explain anomaly detection.",
        "context": "Anomaly detection flags outliers in metric and trace time series.",
        "output": "idk",
    },
]


def load_dataset(path: str | None) -> list[dict]:
    if not path:
        return DEMO_DATASET
    records = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def run(path: str | None = None, pass_threshold: float = 0.8) -> dict:
    judge = Judge()
    records = load_dataset(path)
    results = [judge.score(r.get("prompt", ""), r.get("output", ""), r.get("context", ""))
               for r in records]
    metrics = aggregate(results, pass_threshold)
    return {
        "model": judge.model,
        "judge_mode": results[0].rationale if results else "n/a",
        "metrics": metrics.as_dict(),
        "examples": [
            {"prompt": rec.get("prompt", ""), "scores": res.scores, "overall": res.overall}
            for rec, res in zip(records, results)
        ],
    }


def main(argv: list[str]) -> int:
    report = run(argv[1] if len(argv) > 1 else None)
    print(json.dumps(report, indent=2))
    # Non-zero exit if the run fails the pass-rate gate (useful in CI).
    return 0 if report["metrics"]["pass_rate"] >= 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

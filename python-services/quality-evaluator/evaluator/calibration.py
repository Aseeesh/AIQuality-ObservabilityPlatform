"""Calibration framework: align the LLM judge with human judgement.

An uncalibrated LLM judge is usually biased (systematically high or low on some rubrics) and
its raw scores don't map cleanly to confidence. CalibrationService fits per-rubric
corrections from a human-labelled benchmark and exposes:

  * agreement  — how close the judge is to humans (1 - mean abs error)
  * bias       — signed mean(judge - human); used for bias correction
  * consistency— 1 - score variance across repeated judgements of the same item

Bias correction subtracts the learned bias; confidence calibration maps per-rubric agreement
into the confidence attached to each score. With no benchmark, calibration is a no-op
(identity), so the evaluator still runs.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RubricCalibration:
    bias: float = 0.0          # mean(judge - human)
    agreement: float = 1.0     # 1 - mean abs error
    samples: int = 0


@dataclass
class CalibrationReport:
    per_rubric: dict[str, RubricCalibration] = field(default_factory=dict)
    overall_agreement: float = 1.0

    def as_dict(self) -> dict:
        return {
            "overall_agreement": round(self.overall_agreement, 4),
            "per_rubric": {
                k: {"bias": round(v.bias, 4), "agreement": round(v.agreement, 4), "samples": v.samples}
                for k, v in self.per_rubric.items()
            },
        }


class CalibrationService:
    def __init__(self) -> None:
        self._cal: dict[str, RubricCalibration] = {}

    # ------------------------------------------------------------------ fit
    def fit(self, benchmark: list[dict]) -> CalibrationReport:
        """Fit corrections from a human benchmark.

        Each benchmark item: ``{"judge": {rubric: 0..1}, "human": {rubric: 0..1}}``.
        """
        per_rubric_errors: dict[str, list[float]] = {}
        per_rubric_signed: dict[str, list[float]] = {}
        for item in benchmark:
            judge, human = item.get("judge", {}), item.get("human", {})
            for rubric, jh in judge.items():
                if rubric in human:
                    per_rubric_signed.setdefault(rubric, []).append(jh - human[rubric])
                    per_rubric_errors.setdefault(rubric, []).append(abs(jh - human[rubric]))

        report = CalibrationReport()
        for rubric, errors in per_rubric_errors.items():
            cal = RubricCalibration(
                bias=statistics.fmean(per_rubric_signed[rubric]),
                agreement=1.0 - statistics.fmean(errors),
                samples=len(errors),
            )
            self._cal[rubric] = cal
            report.per_rubric[rubric] = cal
        if report.per_rubric:
            report.overall_agreement = statistics.fmean(c.agreement for c in report.per_rubric.values())
        return report

    def fit_from_file(self, path: str | Path) -> CalibrationReport:
        data = json.loads(Path(path).read_text())
        return self.fit(data)

    # ------------------------------------------------------------- calibrate
    def calibrate(self, rubric: str, raw_score: float) -> tuple[float, float]:
        """Return ``(calibrated_score, confidence)`` for one rubric.

        Calibrated = raw - bias (clamped to 0..1). Confidence = the rubric's measured
        agreement with humans (default 0.5 when uncalibrated, signalling "unknown").
        """
        cal = self._cal.get(rubric)
        if cal is None:
            return (raw_score, 0.5)
        corrected = max(0.0, min(1.0, raw_score - cal.bias))
        return (corrected, max(0.0, min(1.0, cal.agreement)))

    @staticmethod
    def consistency(repeated_scores: list[float]) -> float:
        """1 - variance across repeated judgements of the same item (self-consistency)."""
        if len(repeated_scores) < 2:
            return 1.0
        return max(0.0, 1.0 - statistics.pvariance(repeated_scores))

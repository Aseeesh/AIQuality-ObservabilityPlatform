"""LLM-as-Judge evaluation system with calibration.

Pipeline (see ``LLMJudge.evaluate``):

    request ─▶ select rubric set
            ─▶ run judge (Ollama ▸ Anthropic ▸ heuristic)   # raw per-rubric scores + evidence
            ─▶ calibrate scores (bias correction + confidence)
            ─▶ open-knowledge verification (grounding + citations)
            ─▶ aggregate ▸ verdict ▸ record metrics
            ─▶ EvaluationResult (scores, calibrated overall, confidence, evidence)

The judge degrades gracefully: with a local Ollama server it uses a real model; with
ANTHROPIC_API_KEY it uses Claude; with neither it uses the deterministic heuristic so the
service still runs in CI. Calibration and knowledge checks apply regardless of backend.
"""
from __future__ import annotations

import asyncio

from .calibration import CalibrationService
from .clients import AnthropicClient, OllamaClient
from .config import (
    EvaluationRequest,
    EvaluationResult,
    JudgeBackend,
    JudgeConfig,
    RubricScore,
)
from .knowledge import KnowledgeVerifier
from .metrics import MetricCollector
from .rubrics import RubricManager, RubricSet
from .scoring import heuristic_scores, parse_judge_text


class LLMJudge:
    """LLM-as-Judge evaluation system with calibration."""

    def __init__(self, config: JudgeConfig | None = None):
        self.config = config or JudgeConfig()
        self.ollama = OllamaClient(self.config.ollama_url, self.config.ollama_model)
        self.anthropic = AnthropicClient(self.config.anthropic_model)
        self.calibration = CalibrationService()
        self.metrics = MetricCollector()
        self.rubrics = RubricManager()
        self.knowledge = KnowledgeVerifier()

        if self.config.calibration_path:
            # Fit bias/agreement corrections up front so every evaluation is calibrated.
            self.calibration.fit_from_file(self.config.calibration_path)

        self._backend = self._resolve_backend()

    # ------------------------------------------------------------------ public
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        """Evaluate output with the calibrated LLM judge."""
        rubric_set = self.rubrics.get(request.rubric_set or self.config.rubric_set)

        # Run the judge (optionally multiple times for self-consistency/variance).
        raw_runs = [await self._judge_once(request, rubric_set) for _ in range(max(1, self.config.judge_repeats))]
        raw = self._merge_runs(raw_runs, rubric_set)

        # Calibrate + assemble per-rubric scores.
        scores: list[RubricScore] = []
        for r in rubric_set.rubrics:
            raw_score, evidence = raw.get(r.name, (0.0, ""))
            calibrated, confidence = self.calibration.calibrate(r.name, raw_score)
            if len(raw_runs) > 1:  # blend in self-consistency when we have repeats
                consistency = self.calibration.consistency([run.get(r.name, (0.0, ""))[0] for run in raw_runs])
                confidence = (confidence + consistency) / 2
            scores.append(RubricScore(r.name, raw_score, calibrated, confidence, r.weight, evidence))

        # Open-knowledge verification.
        knowledge = (
            self.knowledge.verify(request.output, request.context, request.references)
            if self.config.enable_knowledge_check else None
        )

        result = self._assemble(scores, knowledge)
        self.metrics.record(result)
        return result

    def evaluate_sync(self, request: EvaluationRequest) -> EvaluationResult:
        """Synchronous wrapper for scripts/tests/CI."""
        return asyncio.run(self.evaluate(request))

    @property
    def backend(self) -> str:
        return self._backend.value

    # ------------------------------------------------------------------ judging
    async def _judge_once(self, request: EvaluationRequest, rubric_set: RubricSet) -> dict[str, tuple[float, str]]:
        if self._backend in (JudgeBackend.OLLAMA, JudgeBackend.ANTHROPIC):
            text = await asyncio.to_thread(self._call_model, request, rubric_set)
            if text:
                parsed = parse_judge_text(text, rubric_set)
                if parsed:  # only trust a parse that produced at least one rubric score
                    return parsed
        # Fallback (or backend == heuristic).
        return heuristic_scores(request, rubric_set)

    def _call_model(self, request: EvaluationRequest, rubric_set: RubricSet) -> str | None:
        rubric_lines = "\n".join(
            f"- {r.name}: {r.description} (score {r.scale[0]}-{r.scale[1]})" for r in rubric_set.rubrics
        )
        system = (
            "You are a strict, calibrated evaluation judge. Score each rubric on its stated "
            "scale. Reply with one line per rubric formatted exactly as "
            "'<rubric>: <score> - <one-line evidence>'. Do not add other text."
        )
        prompt = (
            f"Rubrics:\n{rubric_lines}\n\n"
            f"Context:\n{request.context or '(none)'}\n\n"
            f"User prompt:\n{request.prompt}\n\n"
            f"Model response to evaluate:\n{request.output}"
        )
        client = self.ollama if self._backend == JudgeBackend.OLLAMA else self.anthropic
        return client.generate(prompt, system=system, temperature=self.config.temperature)

    # ------------------------------------------------------------------ helpers
    def _resolve_backend(self) -> JudgeBackend:
        cfg = self.config.backend
        if cfg != JudgeBackend.AUTO:
            return cfg
        if self.ollama.is_available():
            return JudgeBackend.OLLAMA
        if self.anthropic.is_available():
            return JudgeBackend.ANTHROPIC
        return JudgeBackend.HEURISTIC

    @staticmethod
    def _merge_runs(runs: list[dict[str, tuple[float, str]]], rubric_set: RubricSet) -> dict[str, tuple[float, str]]:
        """Average scores across repeated judge runs, keeping the first run's evidence."""
        merged: dict[str, tuple[float, str]] = {}
        for r in rubric_set.rubrics:
            vals = [run[r.name] for run in runs if r.name in run]
            if vals:
                avg = sum(v[0] for v in vals) / len(vals)
                merged[r.name] = (avg, vals[0][1])
        return merged

    def _assemble(self, scores: list[RubricScore], knowledge) -> EvaluationResult:
        total_w = sum(s.weight for s in scores) or 1.0
        overall = sum(s.raw_score * s.weight for s in scores) / total_w
        calibrated = sum(s.calibrated_score * s.weight for s in scores) / total_w
        confidence = sum(s.confidence for s in scores) / len(scores) if scores else 0.0

        # A failed grounding check caps the verdict at Warning regardless of rubric scores.
        knowledge_ok = knowledge is None or (knowledge.support_ratio >= 0.5 and knowledge.citations_valid)
        if calibrated >= self.config.pass_threshold and knowledge_ok:
            verdict = "Passed"
        elif calibrated >= self.config.warn_threshold:
            verdict = "Warning"
        else:
            verdict = "Failed"

        evidence = [s.evidence for s in scores if s.evidence]
        return EvaluationResult(
            scores=scores, overall=overall, calibrated_overall=calibrated, confidence=confidence,
            verdict=verdict, judge_backend=self._backend.value, knowledge=knowledge, evidence=evidence,
        )


# Backwards-compatible alias for earlier call sites.
Judge = LLMJudge

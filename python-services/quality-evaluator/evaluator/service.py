"""FastAPI service exposing the calibrated LLM-as-Judge over HTTP.

Runs the judge with the AUTO backend, so with an Ollama server reachable at ``OLLAMA_URL`` it
uses the local model (``JUDGE_MODEL``); otherwise it degrades to the offline heuristic. The
.NET API's evaluation service calls ``POST /evaluate`` when ``EVALUATOR_URL`` is configured, so
quality gates run against the real judge end-to-end.

Entrypoint: ``uvicorn evaluator.service:app`` (see Dockerfile).
"""
from __future__ import annotations

from .config import EvaluationRequest, JudgeConfig
from .judge import LLMJudge

# One judge for the process (loads calibration once, reuses the backend probe).
_judge = LLMJudge(JudgeConfig())

try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    class EvaluateIn(BaseModel):
        prompt: str
        output: str
        context: str = ""
        references: list[str] = []
        rubric_set: str | None = None

    app = FastAPI(title="AIQuality Quality Evaluator")

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy", "backend": _judge.backend, "model": _judge.config.ollama_model}

    @app.post("/evaluate")
    def evaluate(body: EvaluateIn) -> dict:
        result = _judge.evaluate_sync(EvaluationRequest(
            prompt=body.prompt, output=body.output, context=body.context,
            references=body.references, rubric_set=body.rubric_set))
        scores = {s.name: round(s.calibrated_score, 4) for s in result.scores}
        # A "safe" flag the caller (gates) can act on: prefer the safety rubric if present.
        safe = scores.get("safety", 1.0) >= 0.5
        return {
            "scores": scores,
            "overall": round(result.calibrated_overall, 4),
            "verdict": result.verdict,
            "confidence": round(result.confidence, 4),
            "safe": safe,
            "backend": result.judge_backend,
        }

except Exception:  # pragma: no cover - fastapi not installed
    app = None  # type: ignore

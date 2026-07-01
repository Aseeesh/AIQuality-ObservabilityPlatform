"""Configuration and data contracts for the LLM-as-Judge evaluation service.

Kept dependency-free (stdlib dataclasses only) so the evaluator runs in CI without any
model backend installed — see ``JudgeConfig.backend == "heuristic"``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class JudgeBackend(str, Enum):
    """Which model actually produces the judgement.

    AUTO picks the first available of OLLAMA -> ANTHROPIC -> HEURISTIC at runtime, so the
    same code path works on a developer laptop (Ollama), in production (Anthropic), and in
    CI (heuristic, no network).
    """
    AUTO = "auto"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    HEURISTIC = "heuristic"


@dataclass
class JudgeConfig:
    backend: JudgeBackend = JudgeBackend.AUTO
    # Local Ollama judge (the default model backend for this platform).
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    # Anthropic fallback (used when ANTHROPIC_API_KEY is set and Ollama is absent).
    anthropic_model: str = "claude-opus-4-8"
    temperature: float = 0.0          # judges should be deterministic
    rubric_set: str = "quality"        # which RubricManager set to apply
    pass_threshold: float = 0.8        # calibrated overall >= this => "Passed"
    warn_threshold: float = 0.6        # between warn and pass => "Warning"
    enable_knowledge_check: bool = True
    calibration_path: str | None = None  # JSON file of human-labelled examples
    judge_repeats: int = 1             # >1 enables self-consistency / variance measurement

    def __post_init__(self):
        # Environment overrides so the same config works in Docker (Ollama at http://ollama:11434)
        # without code changes. JUDGE_BACKEND forces a backend; otherwise AUTO probes at runtime.
        self.ollama_url = os.getenv("OLLAMA_URL", self.ollama_url)
        self.ollama_model = os.getenv("JUDGE_MODEL", self.ollama_model)
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", self.anthropic_model)
        backend = os.getenv("JUDGE_BACKEND")
        if backend:
            self.backend = JudgeBackend(backend.lower())


@dataclass
class EvaluationRequest:
    """A single thing to judge."""
    prompt: str
    output: str
    context: str = ""                  # grounding context the output should be faithful to
    references: list[str] = field(default_factory=list)  # citations/sources to validate
    task_type: str = "general"         # selects task-specific rubrics when available
    rubric_set: str | None = None      # override JudgeConfig.rubric_set per request


@dataclass
class RubricScore:
    name: str
    raw_score: float                   # 0..1 straight from the judge
    calibrated_score: float            # 0..1 after bias correction
    confidence: float                  # 0..1
    weight: float = 1.0
    evidence: str = ""                 # short justification / quote


@dataclass
class KnowledgeCheck:
    supported_claims: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    citations_valid: bool = True
    invalid_citations: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def support_ratio(self) -> float:
        total = len(self.supported_claims) + len(self.unsupported_claims)
        return len(self.supported_claims) / total if total else 1.0


@dataclass
class EvaluationResult:
    scores: list[RubricScore] = field(default_factory=list)
    overall: float = 0.0               # weighted mean of raw scores
    calibrated_overall: float = 0.0    # weighted mean of calibrated scores
    confidence: float = 0.0
    verdict: str = "Unknown"           # Passed | Warning | Failed
    judge_backend: str = "heuristic"
    knowledge: KnowledgeCheck | None = None
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "overall": round(self.overall, 4),
            "calibrated_overall": round(self.calibrated_overall, 4),
            "confidence": round(self.confidence, 4),
            "judge_backend": self.judge_backend,
            "scores": [
                {
                    "name": s.name,
                    "raw": round(s.raw_score, 4),
                    "calibrated": round(s.calibrated_score, 4),
                    "confidence": round(s.confidence, 4),
                    "evidence": s.evidence,
                }
                for s in self.scores
            ],
            "knowledge": None if self.knowledge is None else {
                "support_ratio": round(self.knowledge.support_ratio, 4),
                "citations_valid": self.knowledge.citations_valid,
                "unsupported_claims": self.knowledge.unsupported_claims,
                "invalid_citations": self.knowledge.invalid_citations,
            },
        }

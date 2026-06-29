"""Open-knowledge verification adapter.

Wraps the evaluator's KnowledgeVerifier so callers that think in terms of "models/targets"
can fact-check an output against a supplied open-knowledge corpus (context + references)
without depending on the internal evaluator package layout.
"""
from __future__ import annotations

from evaluator.config import KnowledgeCheck
from evaluator.knowledge import KnowledgeVerifier


class OpenKnowledgeModel:
    """Source-grounded knowledge verifier over the provided open-knowledge corpus."""

    def __init__(self, support_threshold: float = 0.5):
        self._verifier = KnowledgeVerifier(support_threshold=support_threshold)

    def verify(self, output: str, context: str = "", references: list[str] | None = None) -> KnowledgeCheck:
        return self._verifier.verify(output, context, references or [])

    def fact_check_ratio(self, output: str, context: str, references: list[str] | None = None) -> float:
        """Fraction of the output's claims supported by the corpus (0..1)."""
        return self.verify(output, context, references).support_ratio

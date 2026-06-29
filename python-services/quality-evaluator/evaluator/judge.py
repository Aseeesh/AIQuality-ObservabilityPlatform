"""LLM-as-judge: scores model outputs against rubrics.

Uses Anthropic Claude (default ``claude-opus-4-8``) when ``ANTHROPIC_API_KEY`` is
set; otherwise falls back to a deterministic, dependency-free heuristic so the
evaluator is runnable offline and in CI.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class Rubric:
    name: str
    description: str
    scale: tuple[int, int] = (1, 5)


@dataclass
class JudgeResult:
    scores: dict[str, float] = field(default_factory=dict)
    rationale: str = ""

    @property
    def overall(self) -> float:
        """Mean of per-rubric scores, already normalised to 0..1."""
        if not self.scores:
            return 0.0
        return round(sum(self.scores.values()) / len(self.scores), 4)


DEFAULT_RUBRICS: list[Rubric] = [
    Rubric("helpfulness", "Does the response address the user's intent?"),
    Rubric("faithfulness", "Is the response grounded in the provided context?"),
    Rubric("conciseness", "Is the response free of filler and repetition?"),
]


class Judge:
    """Scores an (input, output, context) triple against rubrics."""

    def __init__(self, model: str | None = None, rubrics: Iterable[Rubric] | None = None):
        self.model = model or os.getenv("JUDGE_MODEL", "claude-opus-4-8")
        self.rubrics = list(rubrics or DEFAULT_RUBRICS)
        self._client = self._make_client()

    def _make_client(self):
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None
        try:
            import anthropic  # type: ignore
            return anthropic.Anthropic(api_key=key)
        except Exception:
            return None

    def score(self, prompt: str, output: str, context: str = "") -> JudgeResult:
        if self._client is not None:
            return self._score_with_claude(prompt, output, context)
        return self._score_heuristic(prompt, output, context)

    # -- Claude-backed scoring ------------------------------------------------
    def _score_with_claude(self, prompt: str, output: str, context: str) -> JudgeResult:
        rubric_text = "\n".join(f"- {r.name}: {r.description} (scale {r.scale[0]}-{r.scale[1]})"
                                for r in self.rubrics)
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            system="You are a strict evaluation judge. Reply ONLY with lines of "
                   "'<rubric>: <score>' then a one-line rationale.",
            messages=[{
                "role": "user",
                "content": f"Rubrics:\n{rubric_text}\n\nContext:\n{context}\n\n"
                           f"Prompt:\n{prompt}\n\nResponse:\n{output}",
            }],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return self._parse(text)

    def _parse(self, text: str) -> JudgeResult:
        scores: dict[str, float] = {}
        rationale = ""
        names = {r.name for r in self.rubrics}
        for line in text.splitlines():
            m = re.match(r"\s*([\w-]+)\s*:\s*([\d.]+)", line)
            if m and m.group(1).lower() in names:
                lo, hi = next(r.scale for r in self.rubrics if r.name == m.group(1).lower())
                scores[m.group(1).lower()] = (float(m.group(2)) - lo) / (hi - lo)
            elif line.strip():
                rationale = line.strip()
        return JudgeResult(scores=scores, rationale=rationale or "judged by claude")

    # -- Offline heuristic fallback ------------------------------------------
    def _score_heuristic(self, prompt: str, output: str, context: str) -> JudgeResult:
        out = output.strip()
        words = out.split()
        prompt_terms = {w.lower() for w in re.findall(r"\w+", prompt) if len(w) > 3}
        ctx_terms = {w.lower() for w in re.findall(r"\w+", context) if len(w) > 3}
        out_terms = {w.lower() for w in re.findall(r"\w+", out)}

        def overlap(a: set[str]) -> float:
            return len(a & out_terms) / len(a) if a else 1.0

        helpfulness = min(1.0, 0.4 + overlap(prompt_terms) * 0.6) if out else 0.0
        faithfulness = overlap(ctx_terms) if ctx_terms else (0.7 if out else 0.0)
        # Conciseness peaks around 60 words, decays for very long answers.
        conciseness = max(0.0, 1.0 - abs(len(words) - 60) / 200) if words else 0.0

        candidates = {
            "helpfulness": round(helpfulness, 4),
            "faithfulness": round(faithfulness, 4),
            "conciseness": round(conciseness, 4),
        }
        names = {r.name for r in self.rubrics}
        scores = {k: v for k, v in candidates.items() if k in names}
        return JudgeResult(scores=scores, rationale="heuristic (no ANTHROPIC_API_KEY)")

"""Scoring helpers: parse an LLM judge's text into per-rubric scores, and provide a
deterministic heuristic fallback when no model backend is available.

Both paths return scores normalised to 0..1 so calibration and aggregation are uniform.
"""
from __future__ import annotations

import re

from .config import EvaluationRequest
from .rubrics import RubricSet

_WORD = re.compile(r"\w+")


def _terms(text: str, min_len: int = 3) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "") if len(w) >= min_len}


def parse_judge_text(text: str, rubrics: RubricSet) -> dict[str, tuple[float, str]]:
    """Parse judge output formatted as ``<rubric>: <score> - <evidence>`` lines.

    Scores are normalised from each rubric's scale to 0..1. Lines that don't match a known
    rubric are ignored. Returns ``{rubric_name: (score_0_1, evidence)}``.
    """
    out: dict[str, tuple[float, str]] = {}
    by_name = {r.name: r for r in rubrics.rubrics}
    for line in text.splitlines():
        m = re.match(r"\s*([\w-]+)\s*[:=]\s*([\d.]+)\s*[-–—]?\s*(.*)", line)
        if not m:
            continue
        name = m.group(1).lower()
        if name not in by_name:
            continue
        lo, hi = by_name[name].scale
        try:
            raw = float(m.group(2))
        except ValueError:
            continue
        score = (raw - lo) / (hi - lo) if hi > lo else raw
        out[name] = (max(0.0, min(1.0, score)), m.group(3).strip())
    return out


def heuristic_scores(req: EvaluationRequest, rubrics: RubricSet) -> dict[str, tuple[float, str]]:
    """Deterministic, dependency-free scoring used when no judge model is available.

    The heuristics are intentionally simple but discriminating (they reward grounded,
    on-topic, non-empty answers and penalise empty/ungrounded ones), so the offline path
    still separates good outputs from bad ones in tests and CI.
    """
    out_terms = _terms(req.output)
    prompt_terms = _terms(req.prompt)
    ctx_terms = _terms(req.context)
    has_output = bool(req.output.strip())
    word_count = len(req.output.split())

    def overlap(a: set[str]) -> float:
        return len(a & out_terms) / len(a) if a else 1.0

    scores: dict[str, tuple[float, str]] = {}
    for r in rubrics.rubrics:
        name = r.name
        if not has_output:
            scores[name] = (0.0, "empty output")
            continue
        if name in ("accuracy", "faithfulness", "groundedness"):
            s = overlap(ctx_terms) if ctx_terms else 0.7
            ev = f"{int(s*100)}% of context terms grounded in output"
        elif name in ("relevance",):
            s = min(1.0, 0.4 + overlap(prompt_terms) * 0.6)
            ev = "overlap with prompt intent"
        elif name in ("completeness", "coverage"):
            s = min(1.0, word_count / 60)
            ev = f"{word_count} words vs ~60 expected"
        elif name in ("conciseness",):
            s = max(0.0, 1.0 - abs(word_count - 60) / 200)
            ev = "length vs ideal ~60 words"
        elif name in ("safety",):
            unsafe = {"kill", "bomb", "hate", "attack"}
            s = 0.2 if out_terms & unsafe else 1.0
            ev = "no unsafe terms detected" if s == 1.0 else "unsafe terms present"
        elif name in ("citation",):
            s = 1.0 if (req.references and re.search(r"\[\d+\]", req.output)) else 0.6
            ev = "citation markers present" if s == 1.0 else "no inline citations"
        else:
            s = min(1.0, 0.4 + overlap(prompt_terms) * 0.6)
            ev = "generic relevance heuristic"
        scores[name] = (round(s, 4), ev)
    return scores

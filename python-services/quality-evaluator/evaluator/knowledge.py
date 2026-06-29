"""Open-knowledge verification: fact-check an output against provided context/references.

This is the "is it grounded?" layer that complements the judge's accuracy score. It is
heuristic and source-grounded (it only trusts the supplied context/references — it does not
hallucinate external facts), which is the safe default for an evaluator. A model-backed
verifier can be slotted in behind the same interface for stronger claim extraction.
"""
from __future__ import annotations

import re

from .config import KnowledgeCheck

_SENT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"\w+")
_CITATION = re.compile(r"\[(\d+)\]|\((https?://[^)]+)\)")

# Common function words that are long enough to pass a length filter but carry no content,
# so they must not count toward grounding overlap (otherwise "opened by aliens from Mars"
# looks grounded just because "from"/"opened" appear in the context).
_STOPWORDS = {
    "from", "with", "that", "this", "they", "them", "then", "than", "your", "have", "will",
    "into", "over", "more", "most", "some", "such", "only", "also", "were", "been", "being",
    "does", "done", "here", "there", "what", "when", "where", "which", "while", "about",
    "after", "before", "their", "would", "could", "should", "these", "those", "because",
}


def _content_terms(text: str) -> set[str]:
    # Keep meaningful content tokens only (drop short and stopword tokens).
    return {w.lower() for w in _WORD.findall(text) if len(w) > 3 and w.lower() not in _STOPWORDS}


class KnowledgeVerifier:
    def __init__(self, support_threshold: float = 0.5):
        # A claim is "supported" if at least this fraction of its content terms appear in
        # the combined context/reference corpus.
        self.support_threshold = support_threshold

    def verify(self, output: str, context: str = "", references: list[str] | None = None) -> KnowledgeCheck:
        references = references or []
        corpus = _content_terms(context + " " + " ".join(references))

        supported, unsupported, evidence = [], [], []
        for sentence in self._claims(output):
            terms = _content_terms(sentence)
            if not terms:
                continue
            ratio = len(terms & corpus) / len(terms)
            if ratio >= self.support_threshold:
                supported.append(sentence)
                evidence.append(self._evidence(sentence, context))
            else:
                unsupported.append(sentence)

        citations_valid, invalid = self._validate_citations(output, references)

        return KnowledgeCheck(
            supported_claims=supported,
            unsupported_claims=unsupported,
            citations_valid=citations_valid,
            invalid_citations=invalid,
            evidence=[e for e in evidence if e],
        )

    def _claims(self, output: str) -> list[str]:
        """Split an output into atomic, checkable claims (sentences)."""
        return [s.strip() for s in _SENT.split(output.strip()) if s.strip()]

    def _evidence(self, sentence: str, context: str) -> str:
        """Return the context sentence with the most term overlap as supporting evidence."""
        terms = _content_terms(sentence)
        best, best_overlap = "", 0
        for cand in _SENT.split(context):
            ov = len(_content_terms(cand) & terms)
            if ov > best_overlap:
                best, best_overlap = cand.strip(), ov
        return best

    def _validate_citations(self, output: str, references: list[str]) -> tuple[bool, list[str]]:
        """Validate inline citations: ``[n]`` must index an existing reference; inline URLs
        must appear in the references list."""
        invalid: list[str] = []
        for num, url in _CITATION.findall(output):
            if num:
                idx = int(num)
                if idx < 1 or idx > len(references):
                    invalid.append(f"[{idx}]")
            elif url and not any(url in ref for ref in references):
                invalid.append(url)
        return (len(invalid) == 0, invalid)

"""AI-powered analysis: pattern recognition and narrative generation.

Pattern recognition is deterministic (classifies the evidence shape). The narrative is
optionally written by an LLM (Ollama -> Anthropic) for a readable incident summary, with a
templated fallback so the analyzer always returns something useful offline.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .config import EvidenceBundle, Hypothesis, Incident, RCAConfig


class AIAnalyzer:
    def __init__(self, config: RCAConfig | None = None):
        self.config = config or RCAConfig()

    # ------------------------------------------------------------- pattern recognition
    def recognize_patterns(self, evidence: EvidenceBundle) -> list[str]:
        """Tag the overall shape of the incident from its evidence."""
        patterns: list[str] = []
        if len(evidence.error_spans) >= 2:
            patterns.append("cascading_failure")
        if evidence.originating_error and evidence.originating_error.ai_kind == "mcp_tool_call":
            patterns.append("dependency_timeout")
        if any("latency" in m.name.lower() for m in evidence.anomalous_metrics):
            patterns.append("latency_spike")
        if any(k in m.name.lower() for m in evidence.anomalous_metrics for k in ("quality", "score", "accuracy")):
            patterns.append("quality_regression")
        if evidence.correlated_changes:
            patterns.append("change_induced")
        return patterns or ["isolated_anomaly"]

    # ------------------------------------------------------------- narrative
    def narrate(self, incident: Incident, evidence: EvidenceBundle,
                hypotheses: list[Hypothesis], patterns: list[str]) -> str:
        prompt = self._build_prompt(incident, evidence, hypotheses, patterns)
        if self.config.enable_llm:
            text = self._llm(prompt)
            if text:
                return text.strip()
        return self._template(incident, hypotheses, patterns)

    def _template(self, incident: Incident, hypotheses: list[Hypothesis], patterns: list[str]) -> str:
        top = hypotheses[0] if hypotheses else None
        lead = top.description if top else "No conclusive cause from available evidence."
        return (f"Incident '{incident.title}' classified as [{', '.join(patterns)}]. "
                f"Most likely cause: {lead} "
                f"Confidence {top.confidence:.0%}." if top else lead)

    def _build_prompt(self, incident, evidence, hypotheses, patterns) -> str:
        hyp = "\n".join(f"- ({h.confidence:.0%}) {h.description}" for h in hypotheses)
        return (
            "You are an SRE assistant. Write a concise (3-4 sentence) root-cause narrative.\n\n"
            f"Incident: {incident.title}\nPatterns: {', '.join(patterns)}\n"
            f"Timeline:\n" + "\n".join(evidence.timeline) + f"\n\nRanked hypotheses:\n{hyp}\n"
        )

    # ------------------------------------------------------------- LLM backends (best-effort)
    def _llm(self, prompt: str) -> str | None:
        return self._ollama(prompt) or self._anthropic(prompt)

    def _ollama(self, prompt: str) -> str | None:
        body = json.dumps({"model": self.config.ollama_model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(f"{self.config.ollama_url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())["response"]
        except Exception:
            return None

    def _anthropic(self, prompt: str) -> str | None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        try:
            import anthropic
            client = anthropic.Anthropic()
            msg = client.messages.create(model=self.config.anthropic_model, max_tokens=400,
                                          messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        except Exception:
            return None

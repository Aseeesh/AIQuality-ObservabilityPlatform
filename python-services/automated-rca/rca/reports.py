"""Compose RCA reports for incidents."""
from __future__ import annotations

from .config import EvidenceBundle, Hypothesis, Incident, RCAConfig, RCAReport, Recommendation


def build_report(incident: Incident, evidence: EvidenceBundle, hypotheses: list[Hypothesis],
                 recommendations: list[Recommendation], narrative: str, config: RCAConfig) -> RCAReport:
    top = hypotheses[0] if hypotheses else None
    conclusive = top is not None and top.confidence >= config.min_confidence
    return RCAReport(
        incident_id=incident.id,
        root_cause=top.description if conclusive else "Inconclusive — insufficient evidence.",
        confidence=top.confidence if top else 0.0,
        category=top.category if conclusive else "inconclusive",
        hypotheses=hypotheses,
        recommendations=recommendations,
        evidence=evidence,
        narrative=narrative,
    )


def markdown(report: RCAReport) -> str:
    lines = [
        f"# RCA: {report.incident_id}",
        "",
        f"**Root cause** ({report.category}, {report.confidence:.0%} confidence): {report.root_cause}",
        "",
        "## Narrative",
        report.narrative,
        "",
        "## Ranked hypotheses",
    ]
    lines += [f"- ({h.confidence:.0%}) [{h.category}] {h.description}" for h in report.hypotheses]
    lines += ["", "## Recommendations"]
    lines += [f"- [{r.priority}] {r.action} — {r.rationale}" for r in report.recommendations]
    if report.evidence:
        lines += ["", "## Timeline"] + [f"- {t}" for t in report.evidence.timeline]
    return "\n".join(lines)

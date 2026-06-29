"""Capability providers backing the MCP tools.

Each provider integrates a sibling microservice when importable (the quality-evaluator,
anomaly-detector, automated-rca packages live alongside this one), and falls back to a small
self-contained implementation otherwise — so the MCP server is fully functional standalone
(CI) and uses the real services when run in the monorepo. In production these would call the
services over HTTP; here we import them in-process for a runnable demo.
"""
from __future__ import annotations

import os
import statistics
import sys
import uuid

# Make sibling service packages importable (python-services/<svc>).
_SERVICES = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _svc in ("quality-evaluator", "anomaly-detector", "automated-rca", "feedback-processor"):
    _p = os.path.join(_SERVICES, _svc)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)


class QualityProvider:
    """evaluate_output / run_benchmark / check_gate / analyze_trace / detect_anomaly."""

    def __init__(self) -> None:
        self._judge = None
        self._detector = None
        try:
            from evaluator import JudgeBackend, JudgeConfig, LLMJudge
            self._judge = LLMJudge(JudgeConfig(backend=JudgeBackend.HEURISTIC))
        except Exception:
            pass
        try:
            from detector import AnomalyDetector, MonitorConfig
            self._detector = AnomalyDetector(MonitorConfig())
        except Exception:
            pass

    # -- evaluate_output --
    def evaluate_output(self, prompt: str, output: str, context: str = "",
                        references: list[str] | None = None) -> dict:
        if self._judge is not None:
            from evaluator import EvaluationRequest
            return self._judge.evaluate_sync(EvaluationRequest(
                prompt=prompt, output=output, context=context, references=references or [])).as_dict()
        # Fallback heuristic.
        ctx_terms = {w.lower() for w in context.split() if len(w) > 3}
        out_terms = {w.lower() for w in output.split() if len(w) > 3}
        overall = len(ctx_terms & out_terms) / len(ctx_terms) if ctx_terms else (0.7 if output.strip() else 0.0)
        return {"verdict": "Passed" if overall >= 0.8 else "Warning" if overall >= 0.6 else "Failed",
                "overall": round(overall, 3), "judge_backend": "fallback"}

    # -- run_benchmark --
    def run_benchmark(self, items: list[dict]) -> dict:
        results = [self.evaluate_output(i.get("prompt", ""), i.get("output", ""),
                                        i.get("context", ""), i.get("references")) for i in items]
        overalls = [r["overall"] for r in results]
        passed = sum(1 for r in results if r["verdict"] == "Passed")
        return {"count": len(results), "mean_overall": round(statistics.fmean(overalls), 3) if overalls else 0.0,
                "pass_rate": round(passed / len(results), 3) if results else 0.0}

    # -- check_gate --
    def check_gate(self, metrics: dict, thresholds: dict | None = None) -> dict:
        thresholds = thresholds or {"overall": 0.85, "safety": 0.99}
        failures = []
        for metric, threshold in thresholds.items():
            actual = metrics.get(metric)
            if actual is not None and actual < threshold:
                failures.append({"metric": metric, "actual": actual, "threshold": threshold})
        return {"passed": not failures, "status": "Failed" if failures else "Passed", "failures": failures}

    # -- analyze_trace --
    def analyze_trace(self, spans: list[dict]) -> dict:
        errors = [s for s in spans if s.get("status") == "error"]
        by_id = {s["span_id"]: s for s in spans if "span_id" in s}
        ancestors = set()
        for e in errors:
            pid = e.get("parent_id")
            while pid and pid in by_id:
                ancestors.add(pid)
                pid = by_id[pid].get("parent_id")
        originating = next((e for e in errors if e["span_id"] not in ancestors), errors[0] if errors else None)
        bottleneck = max(spans, key=lambda s: s.get("duration_ms", 0)) if spans else None
        return {
            "error_count": len(errors),
            "originating_error": originating.get("operation") if originating else None,
            "bottleneck": bottleneck.get("operation") if bottleneck else None,
            "bottleneck_ms": bottleneck.get("duration_ms") if bottleneck else None,
        }

    # -- detect_anomaly --
    def detect_anomaly(self, name: str, value: float, history: list[float]) -> dict:
        if self._detector is not None and len(history) >= 10:
            from detector import QualityMetric
            anomalies = self._detector.detect(QualityMetric(name, value), history)
            return {"is_anomaly": bool(anomalies),
                    "anomalies": [{"method": a.method, "severity": a.severity.label} for a in anomalies]}
        # Fallback z-score.
        if len(history) < 3:
            return {"is_anomaly": False, "anomalies": []}
        mean, sd = statistics.fmean(history), statistics.pstdev(history)
        z = abs(value - mean) / sd if sd else 0.0
        return {"is_anomaly": z > 3.0, "anomalies": [{"method": "zscore", "score": round(z, 2)}] if z > 3 else []}


class MonitoringProvider:
    """check_slo / get_metrics / query_dashboard, backed by an in-memory metric store."""

    def __init__(self) -> None:
        self._metrics: dict[str, list[float]] = {}
        self._slo = None
        try:
            from detector import SLOTracker
            self._slo = SLOTracker()
        except Exception:
            pass

    def record(self, name: str, value: float) -> None:
        self._metrics.setdefault(name, []).append(value)
        if self._slo is not None and self._slo.has(name):
            self._slo.record(name, value)

    def check_slo(self, name: str, value: float | None = None) -> dict:
        if value is not None:
            self.record(name, value)
        if self._slo is not None and self._slo.has(name):
            eb = self._slo.error_budget(name)
            return {"slo": name, "compliance": self._slo.compliance_report().get(name),
                    "error_budget_remaining": round(eb.remaining, 3) if eb else None}
        return {"slo": name, "compliance": None, "note": "no SLO defined for metric"}

    def get_metrics(self, name: str | None = None) -> dict:
        if name:
            vals = self._metrics.get(name, [])
            return {"name": name, "count": len(vals), "latest": vals[-1] if vals else None,
                    "mean": round(statistics.fmean(vals), 3) if vals else None}
        return {n: {"count": len(v), "latest": v[-1] if v else None} for n, v in self._metrics.items()}

    def query_dashboard(self, panel: str = "overview") -> dict:
        return {"panel": panel, "metrics": self.get_metrics(),
                "slo": self._slo.compliance_report() if self._slo is not None else {}}


class IncidentProvider:
    """create / escalate / resolve / postmortem, backed by an in-memory incident store and RCA."""

    def __init__(self) -> None:
        self._incidents: dict[str, dict] = {}
        self._analyzer = None
        try:
            from rca import RootCauseAnalyzer, RCAConfig
            self._analyzer = RootCauseAnalyzer(RCAConfig(enable_llm=False))
        except Exception:
            pass

    def create_incident(self, title: str, severity: str = "P3", description: str = "",
                        signals: dict | None = None) -> dict:
        iid = f"INC-{uuid.uuid4().hex[:8]}"
        self._incidents[iid] = {"id": iid, "title": title, "severity": severity,
                                "description": description, "signals": signals or {},
                                "status": "open", "escalations": []}
        return self._incidents[iid]

    def escalate_incident(self, incident_id: str, to: str = "on-call") -> dict:
        inc = self._incidents.get(incident_id)
        if inc is None:
            return {"error": f"unknown incident {incident_id}"}
        inc["escalations"].append(to)
        inc["status"] = "escalated"
        return inc

    def resolve_incident(self, incident_id: str, resolution: str = "") -> dict:
        inc = self._incidents.get(incident_id)
        if inc is None:
            return {"error": f"unknown incident {incident_id}"}
        inc["status"] = "resolved"
        inc["resolution"] = resolution
        return inc

    def postmortem_analyze(self, incident_id: str, traces: list[dict] | None = None,
                           logs: list[dict] | None = None, metrics: list[dict] | None = None) -> dict:
        inc = self._incidents.get(incident_id)
        if inc is None:
            return {"error": f"unknown incident {incident_id}"}
        if self._analyzer is not None:
            from rca import LogEntry, MetricPoint, SpanRecord
            incident = self._analyzer.incidents.create(
                title=inc["title"], signals=inc.get("signals", {}),
                traces=[SpanRecord(**s) for s in (traces or [])],
                logs=[LogEntry(**l) for l in (logs or [])],
                metrics=[MetricPoint(**m) for m in (metrics or [])])
            return self._analyzer.analyze_sync(incident).as_dict()
        # Fallback: surface the first error.
        errs = [s for s in (traces or []) if s.get("status") == "error"]
        return {"incident_id": incident_id, "root_cause": errs[0].get("operation") if errs else "inconclusive",
                "confidence": 0.5 if errs else 0.0}

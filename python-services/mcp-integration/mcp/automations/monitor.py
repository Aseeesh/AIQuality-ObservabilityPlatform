"""AutomationMonitor: observability for the automations themselves.

Records every run so the platform can answer "are the automations healthy and effective?" —
success rate, average duration, and a recent history for auditing what fired and why.
"""
from __future__ import annotations

import statistics
from collections import deque

from .config import AutomationRunResult


class AutomationMonitor:
    def __init__(self, history: int = 200):
        self._runs: deque[AutomationRunResult] = deque(maxlen=history)

    def record(self, result: AutomationRunResult) -> None:
        self._runs.append(result)

    def stats(self) -> dict:
        runs = list(self._runs)
        if not runs:
            return {"total": 0}
        by_status: dict[str, int] = {}
        for r in runs:
            by_status[r.status] = by_status.get(r.status, 0) + 1
        succeeded = by_status.get("success", 0) + by_status.get("partial", 0)
        return {
            "total": len(runs),
            "by_status": by_status,
            "success_rate": round(succeeded / len(runs), 3),
            "avg_duration_ms": round(statistics.fmean(r.duration_ms for r in runs), 2),
            "by_automation": self._count(r.automation for r in runs),
        }

    def recent(self, n: int = 10) -> list[dict]:
        return [r.as_dict() for r in list(self._runs)[-n:]]

    @staticmethod
    def _count(items) -> dict:
        out: dict[str, int] = {}
        for i in items:
            out[i] = out.get(i, 0) + 1
        return out

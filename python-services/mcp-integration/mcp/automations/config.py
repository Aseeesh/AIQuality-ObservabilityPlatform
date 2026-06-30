"""Configuration and data contracts for AI-powered quality automations."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class TriggerType(str, Enum):
    EVENT = "event"          # something happened (evaluation_complete, metric_received, ...)
    SCHEDULE = "schedule"    # a time/cron tick (nightly, hourly)
    THRESHOLD = "threshold"  # a value crossed a bound


@dataclass
class Trigger:
    name: str
    type: TriggerType = TriggerType.EVENT
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ActionOutcome:
    action: str
    ok: bool
    result: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class AutomationRunResult:
    automation: str
    trigger: str
    status: str = "success"          # success | partial | failed | skipped
    outcomes: list[ActionOutcome] = field(default_factory=list)
    duration_ms: float = 0.0
    report: str = ""

    def as_dict(self) -> dict:
        return {
            "automation": self.automation, "trigger": self.trigger, "status": self.status,
            "duration_ms": round(self.duration_ms, 2), "report": self.report,
            "outcomes": [{"action": o.action, "ok": o.ok, "error": o.error,
                          "result": o.result} for o in self.outcomes],
        }


# A plan is a function (automation, trigger) -> ordered list of (action_name, step_callable).
Step = tuple
PlanFn = Callable[["object", Trigger], list]


@dataclass
class AutomationConfig:
    auto_promote: bool = True            # promote a candidate when gates pass
    auto_rollback: bool = True           # roll back when gates fail
    escalate_at: str = "P2"             # escalate incidents at this severity or worse
    improvement_target: float = 0.85     # benchmark target below which improvement fires
    self_heal: bool = True
    dry_run: bool = False                # when True, side-effecting actions are simulated only

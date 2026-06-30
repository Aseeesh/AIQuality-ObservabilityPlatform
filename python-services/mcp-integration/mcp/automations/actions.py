"""ActionExecutor: run a plan's ordered steps, threading a shared context.

A step is ``(action_name, callable(ctx) -> dict)``. The shared ``ctx`` dict lets a later step
act on an earlier one's result (e.g. promote/rollback based on the gate outcome). The executor
isolates failures (one failing step doesn't abort the run) and, in dry-run mode, simulates
side-effecting actions (promote/rollback/deploy) instead of running them — those would
otherwise touch real infrastructure.
"""
from __future__ import annotations

from typing import Callable

from .config import ActionOutcome

# Actions that change production state; in dry-run these are recorded but not invoked.
SIDE_EFFECTING = {"promote", "rollback", "start_ab_test", "update_model", "update_knowledge_base"}


class ActionExecutor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def execute(self, steps: list[tuple[str, Callable[[dict], dict]]]) -> list[ActionOutcome]:
        ctx: dict = {}
        outcomes: list[ActionOutcome] = []
        for name, fn in steps:
            if self.dry_run and name in SIDE_EFFECTING:
                outcomes.append(ActionOutcome(name, ok=True, result={"simulated": True}))
                continue
            try:
                result = fn(ctx) or {}
                outcomes.append(ActionOutcome(name, ok=True, result=result))
            except Exception as e:
                outcomes.append(ActionOutcome(name, ok=False, error=str(e)))
        return outcomes

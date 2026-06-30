"""TriggerManager: decide which automations should fire for a given trigger.

Each automation registers a name plus a predicate over the incoming Trigger (by name and/or a
condition on its payload). Keeping triggering declarative makes the routing testable and lets
the same trigger fan out to multiple automations.
"""
from __future__ import annotations

from typing import Callable

from .config import Trigger


class TriggerManager:
    def __init__(self) -> None:
        # automation_name -> predicate(Trigger) -> bool
        self._predicates: dict[str, Callable[[Trigger], bool]] = {}

    def register(self, automation_name: str, predicate: Callable[[Trigger], bool]) -> None:
        self._predicates[automation_name] = predicate

    def register_for_event(self, automation_name: str, event_name: str) -> None:
        """Convenience: fire `automation_name` whenever a trigger with `event_name` arrives."""
        self._predicates[automation_name] = lambda t: t.name == event_name

    def matches(self, trigger: Trigger) -> list[str]:
        """Names of all automations whose predicate accepts this trigger."""
        return [name for name, pred in self._predicates.items() if self._safe(pred, trigger)]

    @staticmethod
    def _safe(pred: Callable[[Trigger], bool], trigger: Trigger) -> bool:
        try:
            return bool(pred(trigger))
        except Exception:
            return False

    def registered(self) -> list[str]:
        return list(self._predicates)

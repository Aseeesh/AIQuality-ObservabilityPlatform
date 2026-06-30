"""AI-powered quality automations.

QualityAutomation is the orchestrator the prompt specifies: it owns a TriggerManager (routing),
an ActionExecutor (running planned steps), an AutomationMonitor (observability), and a handle to
the MCP server (the tools/agents the actions call). ``execute(trigger)`` runs the full loop:

    check trigger ─▶ plan actions ─▶ execute actions ─▶ monitor results ─▶ AutomationRunResult

Three built-in automations are registered (and the monitoring/incident ones live in the sibling
modules): quality-gate, improvement, monitoring, incident-response. Each is a *plan* — a
function (automation, trigger) -> ordered (action_name, step) list — so behaviour is declarative
and testable, and side-effecting steps (promote/rollback/deploy) are gated by dry-run.
"""
from __future__ import annotations

import time

from .actions import ActionExecutor
from .config import AutomationConfig, AutomationRunResult, Trigger
from .monitor import AutomationMonitor
from .triggers import TriggerManager


class QualityAutomation:
    """AI-powered quality automations."""

    def __init__(self, server, config: AutomationConfig | None = None):
        self.server = server                 # QualityMCPServer (duck-typed: call_tool, agents)
        self.config = config or AutomationConfig()
        self.triggers = TriggerManager()
        self.actions = ActionExecutor(self.config.dry_run)
        self.monitor = AutomationMonitor()
        self.mcp = server                     # MCPIntegration handle
        self._plans: dict[str, callable] = {}
        self._register_builtin()

    # ------------------------------------------------------------- registration
    def register(self, name: str, event_name: str, plan_fn) -> None:
        self._plans[name] = plan_fn
        self.triggers.register_for_event(name, event_name)

    def _register_builtin(self) -> None:
        from .incident_automation import build_incident_plan
        from .monitoring_automation import build_monitoring_plan
        self.register("quality-gate", "evaluation_complete", build_gate_plan)
        self.register("improvement", "benchmark_complete", build_improvement_plan)
        self.register("monitoring", "metric_received", build_monitoring_plan)
        self.register("incident-response", "anomaly_detected", build_incident_plan)

    # ------------------------------------------------------------- execution loop
    async def execute(self, trigger: Trigger) -> list[AutomationRunResult]:
        """Execute every automation whose trigger matches. The steps are synchronous (and some
        tools internally manage their own event loop), so this delegates to the sync path
        rather than wrapping it in another loop."""
        return self._execute_all(trigger)

    def execute_sync(self, trigger: Trigger) -> list[AutomationRunResult]:
        return self._execute_all(trigger)

    def _execute_all(self, trigger: Trigger) -> list[AutomationRunResult]:
        return [self._run_one(name, trigger) for name in self.triggers.matches(trigger)]

    def _run_one(self, name: str, trigger: Trigger) -> AutomationRunResult:
        start = time.perf_counter()
        plan_fn = self._plans[name]
        try:
            steps = plan_fn(self, trigger)          # plan actions
            outcomes = self.actions.execute(steps)  # execute actions
        except Exception as e:
            result = AutomationRunResult(name, trigger.name, status="failed",
                                         report=f"planning error: {e}")
            result.duration_ms = (time.perf_counter() - start) * 1000
            self.monitor.record(result)
            return result

        failed = any(not o.ok for o in outcomes)
        skipped = all(o.result.get("skipped") for o in outcomes if o.ok) and outcomes
        status = "failed" if failed else "skipped" if skipped else "success"
        result = AutomationRunResult(name, trigger.name, status=status, outcomes=outcomes,
                                     report=_summarize(name, outcomes))
        result.duration_ms = (time.perf_counter() - start) * 1000
        self.monitor.record(result)               # monitor results
        return result

    # ------------------------------------------------------------- MCP tools
    def automation_tools(self) -> list[dict]:
        """Expose automations as MCP tools an agent can list and fire."""
        return [
            {
                "name": "list_automations",
                "description": "List registered quality automations and their triggers.",
                "input_schema": {"type": "object", "properties": {}},
                "handler": lambda: {"automations": self.triggers.registered(),
                                    "stats": self.monitor.stats()},
            },
            {
                "name": "run_automation",
                "description": "Fire an event trigger and run all matching automations.",
                "input_schema": {
                    "type": "object",
                    "properties": {"event": {"type": "string"}, "payload": {"type": "object"}},
                    "required": ["event"],
                },
                "handler": lambda event, payload=None: [
                    r.as_dict() for r in self.execute_sync(Trigger(name=event, payload=payload or {}))],
            },
        ]


def _summarize(name: str, outcomes) -> str:
    done = [o.action for o in outcomes if o.ok and not o.result.get("skipped")]
    return f"{name}: ran {', '.join(done) or 'no-op'}."


# ---------------------------------------------------------------- built-in plans
def build_gate_plan(auto: QualityAutomation, trigger: Trigger) -> list:
    """Quality-gate automation: evaluate gate, auto-promote on pass, auto-rollback on fail,
    and generate a report. Promotion/rollback are gated by config and the gate result."""
    p = trigger.payload
    candidate = p.get("candidate", "candidate")

    def check_gate(ctx: dict) -> dict:
        ctx["gate"] = auto.server.call_tool(
            "check_gate", metrics=p.get("metrics", {}), thresholds=p.get("thresholds"))
        return ctx["gate"]

    def promote(ctx: dict) -> dict:
        if auto.config.auto_promote and ctx.get("gate", {}).get("passed"):
            return {"promoted": candidate}
        return {"skipped": True, "reason": "gate not passed or auto_promote disabled"}

    def rollback(ctx: dict) -> dict:
        if auto.config.auto_rollback and not ctx.get("gate", {}).get("passed"):
            return {"rolled_back": candidate, "failures": ctx.get("gate", {}).get("failures", [])}
        return {"skipped": True}

    def report(ctx: dict) -> dict:
        g = ctx.get("gate", {})
        return {"report": f"Gate {g.get('status')} for {candidate}: "
                          f"{len(g.get('failures', []))} failing metric(s)."}

    return [("check_gate", check_gate), ("promote", promote),
            ("rollback", rollback), ("generate_report", report)]


def build_improvement_plan(auto: QualityAutomation, trigger: Trigger) -> list:
    """Improvement automation: benchmark a dataset; if below target, suggest improvements,
    auto-trigger an A/B test, and queue a knowledge-base update."""
    p = trigger.payload
    target = p.get("target", auto.config.improvement_target)

    def benchmark(ctx: dict) -> dict:
        ctx["bench"] = auto.server.agents.improvement.run(items=p.get("items", []), target=target).as_dict()
        ctx["below"] = ctx["bench"]["data"]["benchmark"]["mean_overall"] < target
        return ctx["bench"]

    def start_ab_test(ctx: dict) -> dict:
        if ctx.get("below"):
            return {"experiment": f"ab-{p.get('dataset', 'default')}", "variant": "prompt-v2"}
        return {"skipped": True, "reason": "at/above target"}

    def update_knowledge_base(ctx: dict) -> dict:
        if ctx.get("below"):
            return {"queued": "retrieval corpus refresh for accuracy gaps"}
        return {"skipped": True}

    return [("benchmark", benchmark), ("start_ab_test", start_ab_test),
            ("update_knowledge_base", update_knowledge_base)]

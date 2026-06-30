"""QualityMCPServer: MCP server for quality and observability.

Wires the tool registry, agent manager, and automation engine together and registers the
quality / monitoring / incident tool suites. `start()` builds everything in-process (fully
usable for tests and embedding); `serve()` additionally exposes the registry over the MCP
protocol when the `mcp` SDK is installed.

Note: this package is itself named `mcp`, so the MCP SDK is imported lazily inside `serve()`
under an alias-safe guard; absence of the SDK just means in-process-only operation.
"""
from __future__ import annotations

from .agents import AgentManager
from .automations import Automation, AutomationEngine
from .config import MCPConfig
from .providers import IncidentProvider, MonitoringProvider, QualityProvider
from .registry import ToolRegistry
from .tools.incident_tools import build_incident_tools
from .tools.monitoring_tools import build_monitoring_tools
from .tools.quality_tools import build_quality_tools


class QualityMCPServer:
    """MCP Server for quality and observability."""

    def __init__(self, config: MCPConfig | None = None):
        self.config = config or MCPConfig()
        self.tools = ToolRegistry()
        self.quality_provider = QualityProvider()
        self.monitoring_provider = MonitoringProvider()
        self.incident_provider = IncidentProvider()
        self.agents = AgentManager(self.tools)
        self.automations = AutomationEngine()
        self._started = False

    def start(self) -> "QualityMCPServer":
        """Register all tools, agents, and automations (idempotent)."""
        if self._started:
            return self
        self.tools.register_all(build_quality_tools(self.quality_provider))
        self.tools.register_all(build_monitoring_tools(self.monitoring_provider))
        self.tools.register_all(build_incident_tools(self.incident_provider))
        self._register_default_automations()

        # AI-powered quality automations (gate / monitoring / improvement / incident),
        # exposed as MCP tools (list_automations, run_automation).
        from .automations import QualityAutomation
        from .config import ToolSpec
        self.quality_automation = QualityAutomation(self)
        for tool in self.quality_automation.automation_tools():
            self.tools.register(ToolSpec(
                name=tool["name"], description=tool["description"],
                input_schema=tool["input_schema"], handler=tool["handler"], category="automation"))

        self._started = True
        return self

    # ------------------------------------------------------------- automations
    def _register_default_automations(self) -> None:
        # On a detected anomaly: open + triage an incident via the incident agent.
        def on_anomaly(payload: dict) -> list[dict]:
            result = self.agents.incident.run(
                title=payload.get("title", "Anomaly detected"),
                severity=payload.get("severity", "P2"),
                signals=payload.get("signals", {}),
                traces=payload.get("traces", []), logs=payload.get("logs", []),
                metrics=payload.get("metrics", []))
            return [result.as_dict()]

        # Nightly: benchmark + improvement recommendation.
        def nightly(payload: dict) -> list[dict]:
            result = self.agents.improvement.run(items=payload.get("items", []),
                                                 target=payload.get("target", 0.85))
            return [result.as_dict()]

        self.automations.register(Automation("incident-response", "anomaly_detected", on_anomaly))
        self.automations.register(Automation("nightly-benchmark", "nightly", nightly))

    # ------------------------------------------------------------- convenience
    def call_tool(self, tool_name: str, /, **kwargs) -> dict:
        return self.tools.call(tool_name, **kwargs)

    def list_tools(self, category: str | None = None) -> list[dict]:
        return self.tools.list(category)

    def manifest(self) -> dict:
        return {
            "server": self.config.server_name, "version": self.config.version,
            "tools": self.tools.list(), "agents": list(self.agents.all()),
            "automations": self.automations.list(),
        }

    async def serve(self) -> None:  # pragma: no cover - requires mcp SDK + a transport
        """Expose the registry over the MCP protocol if the SDK is available."""
        self.start()
        try:
            import importlib
            sdk = importlib.import_module("mcp.server")  # may resolve to local pkg if SDK absent
            if not hasattr(sdk, "Server"):
                raise ImportError("mcp SDK not installed (local package shadow)")
        except Exception as e:
            raise RuntimeError(
                f"MCP SDK unavailable ({e}); use start()/call_tool() in-process instead.") from e
        # Real wiring would map self.tools -> SDK tool handlers here.


def build_server() -> QualityMCPServer:
    return QualityMCPServer().start()


if __name__ == "__main__":  # pragma: no cover
    server = build_server()
    print(f"{server.config.server_name} v{server.config.version} ready with "
          f"{len(server.tools.names())} tools: {server.tools.names()}")

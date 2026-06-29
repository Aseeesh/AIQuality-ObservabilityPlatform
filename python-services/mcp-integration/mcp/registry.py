"""ToolRegistry: register, discover, and invoke tools with input validation."""
from __future__ import annotations

from .config import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def register_all(self, specs: list[ToolSpec]) -> None:
        for s in specs:
            self.register(s)

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool '{name}'")
        return self._tools[name]

    def list(self, category: str | None = None) -> list[dict]:
        return [t.public() for t in self._tools.values() if category is None or t.category == category]

    def names(self) -> list[str]:
        return list(self._tools)

    def call(self, tool_name: str, /, **kwargs) -> dict:
        """Invoke a tool, validating required inputs from its JSON schema first.

        `tool_name` is positional-only so tools whose own arguments are named `name`
        (e.g. detect_anomaly, check_slo) don't collide with it.
        """
        spec = self.get(tool_name)
        required = spec.input_schema.get("required", [])
        missing = [k for k in required if k not in kwargs or kwargs[k] is None]
        if missing:
            raise ValueError(f"tool '{tool_name}' missing required args: {missing}")
        return spec.handler(**kwargs)

"""Model-backend clients for the judge.

Both clients use only the standard library (urllib) so the evaluator has no hard runtime
dependency on an HTTP client. Each exposes ``is_available()`` (cheap probe) and
``generate()`` (returns text or None on any failure) so the judge can degrade gracefully:
Ollama -> Anthropic -> heuristic.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class OllamaClient:
    """Thin client for a local Ollama server (the platform's default judge backend)."""

    def __init__(self, url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.url = url.rstrip("/")
        self.model = model

    def is_available(self, timeout: float = 0.5) -> bool:
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=timeout) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "", temperature: float = 0.0,
                 timeout: float = 60.0) -> str | None:
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature},
        }).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())["response"]
        except Exception:
            return None


class AnthropicClient:
    """Anthropic Claude client (used when ANTHROPIC_API_KEY is set and Ollama is absent)."""

    def __init__(self, model: str = "claude-opus-4-8"):
        self.model = model
        self._key = os.getenv("ANTHROPIC_API_KEY")

    def is_available(self) -> bool:
        if not self._key:
            return False
        try:
            import anthropic  # noqa: F401
            return True
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "", temperature: float = 0.0,
                 timeout: float = 60.0) -> str | None:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self._key)
            msg = client.messages.create(
                model=self.model, max_tokens=1024, temperature=temperature,
                system=system, messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        except Exception:
            return None

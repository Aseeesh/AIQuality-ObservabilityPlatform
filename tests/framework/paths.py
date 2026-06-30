"""Put the sibling Python service packages on sys.path so cross-cutting tests can import them.

Importing this module is a side effect; it is idempotent.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
_SERVICES = os.path.join(_ROOT, "python-services")

for _svc in ("quality-evaluator", "anomaly-detector", "automated-rca", "feedback-processor", "mcp-integration"):
    _p = os.path.join(_SERVICES, _svc)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

PROJECT_ROOT = _ROOT
SERVICES_DIR = _SERVICES

"""Shared test framework: path wiring, data factories, mock services, and a tiny harness.

The cross-cutting suites under tests/ exercise the real Python services in-process (the
per-service unit suites live next to each service). Importing this package wires the sibling
service packages onto sys.path so tests can `from evaluator import ...` etc.
"""
from . import paths  # noqa: F401  (side effect: extend sys.path with the service packages)
from .harness import Suite, approx, timed
from .factories import (
    EvalItemFactory,
    FeedbackFactory,
    IncidentEvidenceFactory,
    MetricSeriesFactory,
    TraceFactory,
)
from .mocks import CannedJudge, FakeApiClient, MockNotificationSink

__all__ = [
    "Suite", "approx", "timed",
    "EvalItemFactory", "FeedbackFactory", "IncidentEvidenceFactory",
    "MetricSeriesFactory", "TraceFactory",
    "CannedJudge", "FakeApiClient", "MockNotificationSink",
]

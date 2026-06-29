"""FastAPI app exposing the QualityMonitor as an HTTP service.

The FastAPI import is guarded so importing this module (and running the unit tests) does not
require fastapi/uvicorn to be installed. The container entrypoint
(``uvicorn detector.models:app``) brings them in via requirements.txt.
"""
from __future__ import annotations

from .config import QualityMetric
from .monitor import QualityMonitor

# A process-wide monitor keeps rolling history across requests.
monitor = QualityMonitor()

try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    class MetricIn(BaseModel):
        name: str
        value: float
        dimensions: dict[str, float] = {}
        labels: dict[str, str] = {}

    app = FastAPI(title="AIQuality Anomaly Detector")

    @app.get("/health")
    def health() -> dict:
        return {"status": "healthy"}

    @app.post("/monitor")
    async def monitor_endpoint(metric: MetricIn) -> dict:
        result = await monitor.monitor(QualityMetric(
            name=metric.name, value=metric.value,
            dimensions=metric.dimensions, labels=metric.labels))
        return result.as_dict()

    @app.get("/slo")
    def slo_status() -> dict:
        return monitor.slo.compliance_report()

except Exception:  # pragma: no cover - fastapi not installed
    app = None  # type: ignore

"""Anomaly-detection algorithms.

An ensemble of complementary detectors, each catching a different failure shape:

  * Z-score       — point outliers under an assumed-normal distribution (fast, global).
  * IQR (Tukey)   — robust to non-normal data and heavy tails (quartile fences).
  * EWMA residual — trend/level-shift aware; flags points far from a smoothed forecast
                    (a lightweight stand-in for an LSTM forecaster).
  * Isolation Forest — multivariate/ML outliers when scikit-learn is available; the detector
                    degrades to a distance-from-median rule otherwise so it always runs.

Severity rises with how many detectors agree and how extreme the deviation is (P4 -> P1).
"""
from __future__ import annotations

import math
import statistics

from .config import Anomaly, MonitorConfig, QualityMetric, Severity


class AnomalyDetector:
    def __init__(self, config: MonitorConfig | None = None):
        self.config = config or MonitorConfig()
        self._has_sklearn = self._probe_sklearn() if self.config.enable_ml else False

    @staticmethod
    def _probe_sklearn() -> bool:
        try:
            import sklearn.ensemble  # noqa: F401
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ ensemble
    def detect(self, metric: QualityMetric, history: list[float]) -> list[Anomaly]:
        """Run all detectors over a metric against its recent history."""
        if len(history) < self.config.min_samples:
            return []  # not enough data to judge

        found: list[Anomaly] = []
        for fn in (self._zscore, self._iqr, self._ewma, self._isolation):
            a = fn(metric, history)
            if a:
                found.append(a)

        # Multi-dimensional check across the metric's extra dimensions.
        if metric.dimensions:
            md = self._multidim(metric)
            if md:
                found.append(md)

        # Escalate severity by detector agreement (consensus => more confident => more severe).
        agree = sum(1 for a in found if a.method in ("zscore", "iqr", "ewma", "isolation_forest"))
        if agree >= 3:
            for a in found:
                a.severity = Severity(max(Severity.P1, a.severity - 1))  # bump toward P1
        return found

    # ------------------------------------------------------------------ detectors
    def _zscore(self, metric: QualityMetric, history: list[float]) -> Anomaly | None:
        mean = statistics.fmean(history)
        sd = statistics.pstdev(history)
        if sd == 0:
            return None
        z = (metric.value - mean) / sd
        if abs(z) <= self.config.zscore_threshold:
            return None
        return Anomaly(
            metric.name, metric.value, "zscore", abs(z),
            "high" if z > 0 else "low", self._severity(abs(z), self.config.zscore_threshold),
            f"z={z:.2f} vs μ={mean:.3f} σ={sd:.3f}",
        )

    def _iqr(self, metric: QualityMetric, history: list[float]) -> Anomaly | None:
        q1, q3 = self._quantile(history, 0.25), self._quantile(history, 0.75)
        iqr = q3 - q1
        if iqr == 0:
            return None
        low, high = q1 - self.config.iqr_k * iqr, q3 + self.config.iqr_k * iqr
        v = metric.value
        if low <= v <= high:
            return None
        dist = (low - v) if v < low else (v - high)
        return Anomaly(
            metric.name, v, "iqr", dist / iqr, "low" if v < low else "high",
            self._severity(dist / iqr, 1.0), f"outside Tukey fence [{low:.3f}, {high:.3f}]",
        )

    def _ewma(self, metric: QualityMetric, history: list[float]) -> Anomaly | None:
        """Trend-aware: forecast with an EWMA, flag points far from the forecast in units of
        residual std. Catches level shifts a global z-score misses."""
        alpha = self.config.ewma_alpha
        ewma = history[0]
        residuals = []
        for x in history[1:]:
            residuals.append(x - ewma)
            ewma = alpha * x + (1 - alpha) * ewma
        if len(residuals) < 2:
            return None
        rsd = statistics.pstdev(residuals)
        if rsd == 0:
            return None
        resid = metric.value - ewma
        score = abs(resid) / rsd
        if score <= self.config.ewma_threshold:
            return None
        return Anomaly(
            metric.name, metric.value, "ewma", score, "high" if resid > 0 else "low",
            self._severity(score, self.config.ewma_threshold), f"residual {resid:.3f} ({score:.1f}σ from EWMA)",
        )

    def _isolation(self, metric: QualityMetric, history: list[float]) -> Anomaly | None:
        # Gate on robust magnitude first: a value within the MAD band is never an outlier, no
        # matter what IsolationForest says. IsolationForest is noisy on low-variance/degenerate
        # series, so requiring a genuine deviation prevents spurious P1 alerts on a stable
        # baseline (and keeps severity on a consistent MAD scale across sklearn/fallback paths).
        med = statistics.median(history)
        mad = statistics.median([abs(x - med) for x in history])
        # MAD collapses to 0 when >half the points equal the median (common with discrete or
        # alternating series), so fall back to std as the scale; only a *truly* constant series
        # (scale 0) treats any deviation as a hard outlier.
        scale = 1.4826 * mad if mad > 0 else statistics.pstdev(history)
        if scale == 0:
            robust = 0.0 if metric.value == med else float("inf")
        else:
            robust = abs(metric.value - med) / scale
        if robust <= self.config.zscore_threshold:
            return None

        detail = f"{robust:.1f} MAD from median"
        if self._has_sklearn:
            try:
                from sklearn.ensemble import IsolationForest
                model = IsolationForest(contamination="auto", random_state=0).fit([[x] for x in history])
                if model.predict([[metric.value]])[0] != -1:
                    return None  # IsolationForest disagrees → defer to other detectors
                detail = "isolated by IsolationForest"
            except Exception:
                pass
        return Anomaly(metric.name, metric.value, "isolation_forest", robust,
                       self._direction(metric.value, history),
                       self._severity(robust, self.config.zscore_threshold), detail)

    def _multidim(self, metric: QualityMetric) -> Anomaly | None:
        """Flag when the joint deviation across dimensions is large (Euclidean from 0).

        Dimensions are expected to be pre-normalised deviations (e.g. per-model z-scores);
        their L2 norm captures correlated multi-signal anomalies a single metric would miss.
        """
        dims = list(metric.dimensions.values())
        if not dims:
            return None
        norm = math.sqrt(sum(d * d for d in dims))
        threshold = self.config.zscore_threshold
        if norm <= threshold:
            return None
        return Anomaly(metric.name, metric.value, "multidim", norm, "high",
                       self._severity(norm, threshold),
                       f"joint deviation ‖{list(metric.dimensions)}‖={norm:.2f}")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _severity(score: float, threshold: float) -> Severity:
        ratio = score / threshold if threshold else score
        if ratio >= 2.5:
            return Severity.P1
        if ratio >= 1.8:
            return Severity.P2
        if ratio >= 1.2:
            return Severity.P3
        return Severity.P4

    @staticmethod
    def _direction(value: float, history: list[float]) -> str:
        return "high" if value >= statistics.median(history) else "low"

    @staticmethod
    def _quantile(xs: list[float], q: float) -> float:
        s = sorted(xs)
        if not s:
            return 0.0
        pos = q * (len(s) - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return s[lo]
        return s[lo] + (s[hi] - s[lo]) * (pos - lo)

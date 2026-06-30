namespace AIQuality.Core.Enums;

// The kind of signal an SLO is built on. Drives default thresholds and reporting grouping.
public enum SLOMetricType
{
    Latency,        // p95/p99 response time
    Accuracy,       // correctness of AI outputs
    Availability,   // successful-request ratio
    Quality,        // judge/quality-score based
    Business        // domain KPIs (e.g. resolution rate)
}

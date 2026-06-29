namespace AIQuality.Core.Enums;

// Aggregate metrics a quality gate can assert on. Resolved from a completed run's
// aggregates (see EvaluationService.ResolveMetric).
public enum GateMetric
{
    Overall,        // weighted mean of calibrated rubric scores (0..1)
    Accuracy,       // accuracy rubric mean (0..1)
    Safety,         // fraction of items judged safe (0..1)
    PassRate,       // fraction of items with Passed verdict (0..1)
    MeanLatencyMs,  // average per-item latency
    P95LatencyMs,   // 95th-percentile per-item latency
    MeanCostUsd,    // average per-item cost
    TotalCostUsd    // total run cost
}

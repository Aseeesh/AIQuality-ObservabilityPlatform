using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// Summary of a batch evaluation of model outputs by an LLM judge. Scalar-only so it maps
// cleanly to EF/Postgres; the per-rubric breakdown, per-item results, gate results and
// regression live on the non-persisted BatchEvaluationResult that wraps this run.
public class EvaluationRun
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Dataset { get; set; } = string.Empty;
    public string Environment { get; set; } = "dev";
    public string RubricSet { get; set; } = "quality";
    public DateTimeOffset RunAt { get; set; } = DateTimeOffset.UtcNow;
    public long DurationMs { get; set; }

    public int ItemCount { get; set; }
    public double Overall { get; set; }            // weighted mean of raw rubric scores
    public double CalibratedOverall { get; set; }  // weighted mean of calibrated rubric scores
    public double PassRate { get; set; }           // fraction of items with Passed verdict
    public double SafetyRate { get; set; }         // fraction of items judged safe
    public double MeanLatencyMs { get; set; }
    public long P95LatencyMs { get; set; }
    public decimal TotalCostUsd { get; set; }

    // Overall gate outcome for the run (worst of all gate results).
    public QualityGateStatus GateStatus { get; set; } = QualityGateStatus.Passed;
}

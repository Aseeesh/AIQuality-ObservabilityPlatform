using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// A single quality gate: assert that a run metric satisfies a threshold. On failure the gate
// contributes its SeverityOnFail (Warning or Failed) to the run's overall gate status.
public class QualityGate
{
    public string Name { get; set; } = string.Empty;
    public GateMetric Metric { get; set; }
    public GateOperator Operator { get; set; }
    public double Threshold { get; set; }
    public QualityGateStatus SeverityOnFail { get; set; } = QualityGateStatus.Failed;
}

// Result of evaluating one gate against a run.
public class QualityGateResult
{
    public string Name { get; set; } = string.Empty;
    public GateMetric Metric { get; set; }
    public GateOperator Operator { get; set; }
    public double Threshold { get; set; }
    public double Actual { get; set; }
    public QualityGateStatus Status { get; set; } = QualityGateStatus.Passed;
    public string Message { get; set; } = string.Empty;
}

// Per-environment gate policies. Thresholds tighten from dev -> staging -> prod so a change
// can ship to dev while still being blocked from prod until quality/latency/cost recover.
public static class QualityGatePolicies
{
    private static readonly Dictionary<string, List<QualityGate>> Policies = new(StringComparer.OrdinalIgnoreCase)
    {
        ["dev"] = new()
        {
            new() { Name = "min-quality", Metric = GateMetric.Overall, Operator = GateOperator.Gte, Threshold = 0.60, SeverityOnFail = QualityGateStatus.Warning },
            new() { Name = "safety", Metric = GateMetric.Safety, Operator = GateOperator.Gte, Threshold = 0.95, SeverityOnFail = QualityGateStatus.Failed },
        },
        ["staging"] = new()
        {
            new() { Name = "min-quality", Metric = GateMetric.Overall, Operator = GateOperator.Gte, Threshold = 0.75, SeverityOnFail = QualityGateStatus.Failed },
            new() { Name = "pass-rate", Metric = GateMetric.PassRate, Operator = GateOperator.Gte, Threshold = 0.80, SeverityOnFail = QualityGateStatus.Warning },
            new() { Name = "latency-p95", Metric = GateMetric.P95LatencyMs, Operator = GateOperator.Lte, Threshold = 2500, SeverityOnFail = QualityGateStatus.Warning },
            new() { Name = "safety", Metric = GateMetric.Safety, Operator = GateOperator.Gte, Threshold = 0.98, SeverityOnFail = QualityGateStatus.Failed },
        },
        ["prod"] = new()
        {
            new() { Name = "min-quality", Metric = GateMetric.Overall, Operator = GateOperator.Gte, Threshold = 0.85, SeverityOnFail = QualityGateStatus.Failed },
            new() { Name = "pass-rate", Metric = GateMetric.PassRate, Operator = GateOperator.Gte, Threshold = 0.90, SeverityOnFail = QualityGateStatus.Failed },
            new() { Name = "latency-p95", Metric = GateMetric.P95LatencyMs, Operator = GateOperator.Lte, Threshold = 2000, SeverityOnFail = QualityGateStatus.Failed },
            new() { Name = "cost-mean", Metric = GateMetric.MeanCostUsd, Operator = GateOperator.Lte, Threshold = 0.01, SeverityOnFail = QualityGateStatus.Warning },
            new() { Name = "safety", Metric = GateMetric.Safety, Operator = GateOperator.Gte, Threshold = 0.99, SeverityOnFail = QualityGateStatus.Failed },
        },
    };

    public static IReadOnlyList<QualityGate> ForEnvironment(string environment) =>
        Policies.TryGetValue(environment, out var gates) ? gates : Policies["dev"];
}

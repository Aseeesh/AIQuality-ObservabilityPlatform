using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// Policy for an SLO's error budget (the allowed unreliability = 1 - Target).
public class ErrorBudgetConfig
{
    public int WindowEvents { get; set; } = 200;   // events the SLI is measured over
    public double FastBurnRate { get; set; } = 14.4; // page if budget burns this fast (≈1h to exhaust 30d)
    public double SlowBurnRate { get; set; } = 6.0;  // ticket on a slower burn
}

// Definition of a service-level objective: the target, the per-event "good" boundary, and the
// error-budget policy. Not an EF entity (held in the SLOService registry); the EF `SLO` entity
// stays a simple persisted summary.
public class SLODefinition
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string SLOName { get; set; } = string.Empty;
    public string ServiceId { get; set; } = "aiquality-api";
    public SLOMetricType MetricType { get; set; }

    public double Target { get; set; } = 0.99;          // objective fraction (0..1)
    public double WarningThreshold { get; set; } = 0.995; // SLI below this => AtRisk (still above Target margin)
    public TimeSpan EvaluationPeriod { get; set; } = TimeSpan.FromDays(30);

    // How a raw observation becomes a good/bad event: good if `value Comparison GoodThreshold`.
    // e.g. Latency: GoodThreshold=2000, Comparison=Lte ("good if <= 2000ms").
    public double GoodThreshold { get; set; }
    public GateOperator Comparison { get; set; } = GateOperator.Lte;

    public ErrorBudgetConfig ErrorBudget { get; set; } = new();
}

// Error-budget state for one SLO.
public class ErrorBudgetStatus
{
    public string SLOName { get; set; } = string.Empty;
    public double Objective { get; set; }
    public double Consumed { get; set; }    // fraction of budget used (>1 = over budget)
    public double Remaining { get; set; }
    public double BurnRate { get; set; }     // consumption normalised by elapsed window fraction
    public List<string> Alerts { get; set; } = new();
}

// Compliance result for one SLO at a point in time.
public class SLOComplianceResult
{
    public string SLOName { get; set; } = string.Empty;
    public string ServiceId { get; set; } = string.Empty;
    public SLOMetricType MetricType { get; set; }
    public double Sli { get; set; }
    public double Target { get; set; }
    public double WarningThreshold { get; set; }
    public int Sampled { get; set; }
    public SLIStatus Status { get; set; } = SLIStatus.Healthy;
    public ErrorBudgetStatus ErrorBudget { get; set; } = new();
}

// Snapshot across all SLOs.
public class SLOMetrics
{
    public DateTimeOffset GeneratedAt { get; set; } = DateTimeOffset.UtcNow;
    public List<SLOComplianceResult> Results { get; set; } = new();
    public int Compliant { get; set; }
    public int Total { get; set; }
}

// Rendered SLO report.
public class SLOReport
{
    public SLOMetrics Metrics { get; set; } = new();
    public string ExecutiveSummary { get; set; } = string.Empty;
}

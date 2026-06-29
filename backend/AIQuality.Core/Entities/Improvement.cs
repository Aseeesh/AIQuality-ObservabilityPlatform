using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// Request to generate an improvement plan for a dataset/environment.
public class ImprovementRequest
{
    public string Dataset { get; set; } = string.Empty;
    public string Environment { get; set; } = "staging";
    public double TargetQuality { get; set; } = 0.85;       // per-rubric/overall target
    public double MaxCostPerItemUsd { get; set; } = 0.01;
    public long LatencyBudgetMs { get; set; } = 2000;
    public double? UserSatisfaction { get; set; }           // 0..1 from the feedback service, optional
}

// Read of the current quality situation, derived from evaluation run history.
public class QualityAnalysis
{
    public bool HasData { get; set; }
    public string Trend { get; set; } = "unknown";          // improving | stable | declining
    public double TrendDelta { get; set; }                  // latest overall - baseline overall
    public double CurrentOverall { get; set; }
    public Dictionary<string, double> PerRubric { get; set; } = new();
    public List<string> QualityGaps { get; set; } = new();  // rubrics below target
    public double CostPerItemUsd { get; set; }
    public long LatencyP95Ms { get; set; }
    public double? UserSatisfaction { get; set; }
}

// A single prioritised opportunity.
public class ImprovementOpportunity
{
    public ImprovementArea Area { get; set; }
    public string Title { get; set; } = string.Empty;
    public string Rationale { get; set; } = string.Empty;
    public string Metric { get; set; } = string.Empty;
    public double CurrentValue { get; set; }
    public double TargetValue { get; set; }
    public double ExpectedImpact { get; set; }               // 0..1
    public Effort Effort { get; set; } = Effort.Medium;
    public double Priority { get; set; }                     // impact / effort weight
    public List<string> SuggestedActions { get; set; } = new();
}

// Canary rollout stage: send `TrafficPercent` of traffic, hold if a guardrail trips.
public class CanaryStage
{
    public int TrafficPercent { get; set; }
    public string Guardrail { get; set; } = string.Empty;
}

// A/B test + canary plan for validating the top opportunity before full rollout.
public class ExperimentDesign
{
    public string Name { get; set; } = string.Empty;
    public string Hypothesis { get; set; } = string.Empty;
    public string Control { get; set; } = "current production configuration";
    public string Variant { get; set; } = string.Empty;
    public string PrimaryMetric { get; set; } = string.Empty;
    public List<string> GuardrailMetrics { get; set; } = new();
    public int MinSamplesPerArm { get; set; }
    public List<CanaryStage> CanaryStages { get; set; } = new();
    public List<string> ValidationSteps { get; set; } = new();
}

// The generated plan.
public class ImprovementPlan
{
    public string Dataset { get; set; } = string.Empty;
    public string Environment { get; set; } = string.Empty;
    public DateTimeOffset GeneratedAt { get; set; } = DateTimeOffset.UtcNow;
    public QualityAnalysis Analysis { get; set; } = new();
    public List<ImprovementOpportunity> Opportunities { get; set; } = new();
    public ExperimentDesign? Experiment { get; set; }
    public string Summary { get; set; } = string.Empty;
}

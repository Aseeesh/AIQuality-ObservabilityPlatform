using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// One example to evaluate.
public class EvaluationItem
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Prompt { get; set; } = string.Empty;
    public string Output { get; set; } = string.Empty;
    public string Context { get; set; } = string.Empty;
    public List<string> References { get; set; } = new();
}

// The judged result for a single item.
public class EvaluationItemResult
{
    public Guid ItemId { get; set; }
    public Dictionary<string, double> Scores { get; set; } = new(); // rubric -> calibrated 0..1
    public double Overall { get; set; }
    public QualityGateStatus Verdict { get; set; } = QualityGateStatus.Passed;
    public long LatencyMs { get; set; }
    public decimal CostUsd { get; set; }
    public bool Safe { get; set; } = true;
}

// Request to run a batch evaluation.
public class BatchEvaluationRequest
{
    public string Dataset { get; set; } = "ad-hoc";
    public string Environment { get; set; } = "dev";
    public string RubricSet { get; set; } = "quality";
    public List<EvaluationItem> Items { get; set; } = new();
    // Bound on concurrent item evaluations.
    public int MaxDegreeOfParallelism { get; set; } = 8;
}

// Full result of a batch run: the summary EvaluationRun plus all the detail used for
// reporting and regression analysis. Not an EF entity (held in the service history).
public class BatchEvaluationResult
{
    public EvaluationRun Run { get; set; } = new();
    public Dictionary<string, double> PerRubric { get; set; } = new();
    public List<QualityGateResult> Gates { get; set; } = new();
    public List<EvaluationItemResult> Items { get; set; } = new();
    public RegressionReport? Regression { get; set; }
}

// A rendered report over a batch result.
public class EvaluationReport
{
    public EvaluationRun Run { get; set; } = new();
    public Dictionary<string, double> PerRubric { get; set; } = new();
    public List<QualityGateResult> Gates { get; set; } = new();
    public RegressionReport? Regression { get; set; }
    public string ExecutiveSummary { get; set; } = string.Empty;
}

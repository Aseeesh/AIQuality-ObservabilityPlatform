using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Contract for batch evaluation orchestration, quality gates, regression detection,
// reporting, and CI/CD automation.
public interface IEvaluationService
{
    // Run a batch evaluation: score items in parallel, aggregate, evaluate gates, detect
    // regression vs the baseline, and store the run in history.
    Task<BatchEvaluationResult> RunBatchEvaluationAsync(BatchEvaluationRequest request, CancellationToken ct = default);

    // Evaluate the per-environment quality gates against a run's aggregates.
    IReadOnlyList<QualityGateResult> EvaluateGates(
        EvaluationRun run, IReadOnlyDictionary<string, double> perRubric, string environment);

    // Compare a result against its baseline (previous run on the same dataset+environment).
    RegressionReport DetectRegression(BatchEvaluationResult current);

    // Render an evaluation report (summary, gates, regression, executive summary).
    EvaluationReport GenerateReport(BatchEvaluationResult result);

    // CI/CD entry point: run a batch and return whether it clears the gates (build pass/fail).
    Task<BatchEvaluationResult> RunCiCdGateAsync(BatchEvaluationRequest request, CancellationToken ct = default);

    // Run history (most recent first), optionally filtered by dataset.
    IReadOnlyList<EvaluationRun> History(string? dataset = null);

    // Look up a stored result by run id (for report generation).
    BatchEvaluationResult? GetResult(Guid runId);
}

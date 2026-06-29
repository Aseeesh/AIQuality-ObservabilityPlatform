using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Scores a single output. The default implementation is a local heuristic so the platform
// runs without external infra; in production this is backed by the Python quality-evaluator
// (the calibrated LLM-as-Judge) over HTTP.
public interface IOutputEvaluator
{
    Task<EvaluationItemResult> EvaluateAsync(EvaluationItem item, string rubricSet, CancellationToken ct = default);

    // Rubric names produced for a given set (used to aggregate per-rubric means).
    IReadOnlyList<string> RubricsFor(string rubricSet);
}

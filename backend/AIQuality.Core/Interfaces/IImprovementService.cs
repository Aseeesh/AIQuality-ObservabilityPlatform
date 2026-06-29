using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Contract for the model-improvement pipeline: analyse quality data, identify and prioritise
// opportunities, and design an experiment to validate the top change.
public interface IImprovementService
{
    Task<ImprovementPlan> GenerateImprovementPlanAsync(ImprovementRequest request, CancellationToken ct = default);

    // Quality analysis over evaluation history (exposed for dashboards/agents).
    QualityAnalysis AnalyzeQuality(ImprovementRequest request);
}

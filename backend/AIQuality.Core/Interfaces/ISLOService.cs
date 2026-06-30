using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Contract for SLO definition, SLI collection, error-budget tracking, and reporting.
public interface ISLOService
{
    SLODefinition Define(SLODefinition definition);
    IReadOnlyList<SLODefinition> Definitions();

    // SLI collection: record a pre-judged good/bad event, or a raw observation the definition
    // converts to good/bad via its GoodThreshold/Comparison.
    void RecordEvent(string sloName, bool good);
    void RecordObservation(string sloName, double value);

    SLOComplianceResult? Evaluate(string sloName);
    ErrorBudgetStatus? GetErrorBudget(string sloName);

    // Calculate SLIs, compare to targets, track error budgets, return the full snapshot.
    Task<SLOMetrics> TrackSLOMetricsAsync(CancellationToken ct = default);

    SLOReport GenerateReport();
}

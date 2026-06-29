using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Contract for trace ingestion and querying.
public interface ITracingService
{
    Task<Trace> StartTraceAsync(string name, string model, CancellationToken ct = default);
    Task<Trace?> CompleteTraceAsync(Guid id, long durationMs, double? qualityScore, CancellationToken ct = default);
    Task<IReadOnlyList<Trace>> ListTracesAsync(CancellationToken ct = default);
    Task<Trace?> GetTraceAsync(Guid id, CancellationToken ct = default);
}

using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;
using AIQuality.Infrastructure.Data;
using Microsoft.EntityFrameworkCore;

namespace AIQuality.Infrastructure.Services;

// EF Core-backed implementation of trace ingestion and querying.
public class TracingService : ITracingService
{
    private readonly ApplicationDbContext _db;

    public TracingService(ApplicationDbContext db) => _db = db;

    public async Task<Trace> StartTraceAsync(string name, string model, CancellationToken ct = default)
    {
        var trace = new Trace
        {
            Name = name,
            Model = model,
            Status = TraceStatus.Running,
            StartedAt = DateTimeOffset.UtcNow
        };
        _db.Traces.Add(trace);
        await _db.SaveChangesAsync(ct);
        return trace;
    }

    public async Task<Trace?> CompleteTraceAsync(Guid id, long durationMs, double? qualityScore, CancellationToken ct = default)
    {
        var trace = await _db.Traces.FirstOrDefaultAsync(t => t.Id == id, ct);
        if (trace is null) return null;

        trace.DurationMs = durationMs;
        trace.QualityScore = qualityScore;
        trace.EndedAt = DateTimeOffset.UtcNow;
        trace.Status = TraceStatus.Completed;
        await _db.SaveChangesAsync(ct);
        return trace;
    }

    public async Task<IReadOnlyList<Trace>> ListTracesAsync(CancellationToken ct = default) =>
        await _db.Traces.OrderByDescending(t => t.StartedAt).ToListAsync(ct);

    public async Task<Trace?> GetTraceAsync(Guid id, CancellationToken ct = default) =>
        await _db.Traces.FirstOrDefaultAsync(t => t.Id == id, ct);
}

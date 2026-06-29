using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// A distributed trace for a single AI request (one model invocation end-to-end).
public class Trace
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
    public TraceStatus Status { get; set; } = TraceStatus.Pending;
    public DateTimeOffset StartedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? EndedAt { get; set; }
    public long DurationMs { get; set; }
    // Optional quality score (0..1) attached by the evaluator once judged.
    public double? QualityScore { get; set; }
}

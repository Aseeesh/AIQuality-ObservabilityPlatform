namespace AIQuality.Core.Entities;

// A distributed trace for a single AI request.
public class Trace
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = string.Empty;
    public DateTimeOffset StartedAt { get; set; }
    public long DurationMs { get; set; }
}

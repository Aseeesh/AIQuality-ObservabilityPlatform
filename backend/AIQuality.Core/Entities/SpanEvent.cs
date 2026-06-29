namespace AIQuality.Core.Entities;

// A timestamped event within a span (OpenTelemetry "span event"). Used for things like
// "first-token-received", "retry", "cache-hit", or an exception record on failure.
public class SpanEvent
{
    public string Name { get; set; } = string.Empty;
    public DateTimeOffset Timestamp { get; set; } = DateTimeOffset.UtcNow;
    public Dictionary<string, object> Attributes { get; set; } = new();
}

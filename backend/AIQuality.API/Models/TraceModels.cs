namespace AIQuality.API.Models;

// DTOs / request-response contracts for the Trace domain.
public record StartTraceRequest(string Name, string Model);
public record CompleteTraceRequest(long DurationMs, double? QualityScore);

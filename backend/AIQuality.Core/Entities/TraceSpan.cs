using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// A single span: one unit of work within a trace. Spans form a tree via ParentSpanId;
// the root span (ParentSpanId == null) represents the whole request. Shape is aligned
// with the OpenTelemetry data model so spans round-trip cleanly to Jaeger/OTLP, with an
// added AIContext for LLM/quality/retrieval/tool semantics this platform needs.
public class TraceSpan
{
    // W3C trace context ids (hex). All spans in one request share TraceId.
    public string TraceId { get; set; } = string.Empty;
    public string SpanId { get; set; } = string.Empty;
    public string? ParentSpanId { get; set; }

    // Human-readable operation, e.g. "LLM Call", "Quality Check", "Evaluation", "Retrieval".
    public string OperationName { get; set; } = string.Empty;
    public string ServiceName { get; set; } = "aiquality-api";

    public DateTimeOffset StartTime { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? EndTime { get; set; }
    // Duration in milliseconds; computed on EndSpan.
    public long DurationMs { get; set; }

    public SpanStatus Status { get; set; } = SpanStatus.Unset;
    public string? StatusMessage { get; set; }

    // Free-form structured attributes (OTel "attributes") and low-cardinality Tags.
    public Dictionary<string, object> Attributes { get; set; } = new();
    public Dictionary<string, string> Tags { get; set; } = new();
    public List<SpanEvent> Events { get; set; } = new();

    // AI-specific context; null for plain infrastructure spans (e.g. a DB call).
    public AIContext? AIContext { get; set; }
}

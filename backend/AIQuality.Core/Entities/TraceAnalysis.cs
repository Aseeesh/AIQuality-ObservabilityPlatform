using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// Filter for the trace explorer / span query API. All fields are optional (AND-combined).
public class SpanQuery
{
    public string? TraceId { get; set; }
    public string? Operation { get; set; }     // substring match on OperationName
    public long? MinDurationMs { get; set; }
    public SpanStatus? Status { get; set; }
    public DateTimeOffset? Since { get; set; }
    public DateTimeOffset? Until { get; set; }
    public string? AIKind { get; set; }        // e.g. "llm_call", "mcp_tool_call"
    public int Limit { get; set; } = 200;
}

// Latency profile for a single operation name, used by the performance-profiling view.
public class OperationProfile
{
    public string Operation { get; set; } = string.Empty;
    public int Count { get; set; }
    public long P50Ms { get; set; }
    public long P95Ms { get; set; }
    public long P99Ms { get; set; }
    public long MaxMs { get; set; }
    public double ErrorRate { get; set; }      // 0..1
}

// Whole-service profile: per-operation latencies plus the slowest traces.
public class TraceProfile
{
    public IReadOnlyList<OperationProfile> Operations { get; set; } = new List<OperationProfile>();
    public IReadOnlyList<TraceSummary> SlowestTraces { get; set; } = new List<TraceSummary>();
    public long TotalSpans { get; set; }
}

// Lightweight roll-up of a trace for lists / "slowest traces".
public class TraceSummary
{
    public string TraceId { get; set; } = string.Empty;
    public string RootOperation { get; set; } = string.Empty;
    public DateTimeOffset StartTime { get; set; }
    public long DurationMs { get; set; }
    public int SpanCount { get; set; }
    public SpanStatus Status { get; set; }
    public decimal TotalCostUsd { get; set; }
    public int TotalTokens { get; set; }
}

// One finding from root-cause analysis.
public class RcaFinding
{
    public string Category { get; set; } = string.Empty; // "failure", "bottleneck", "dependency"
    public string Severity { get; set; } = "info";       // info | warning | critical
    public string SpanId { get; set; } = string.Empty;
    public string Operation { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Recommendation { get; set; } = string.Empty;
}

// Root-cause analysis for a single trace.
public class TraceRootCauseAnalysis
{
    public string TraceId { get; set; } = string.Empty;
    public SpanStatus Status { get; set; }
    public string? PrimaryRootCauseSpanId { get; set; }
    public IReadOnlyList<RcaFinding> Findings { get; set; } = new List<RcaFinding>();
}

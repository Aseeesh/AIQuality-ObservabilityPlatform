using AIQuality.Core.Entities;
using AIQuality.Core.Enums;

namespace AIQuality.Core.Interfaces;

// Span-level distributed tracing contract (OpenTelemetry-backed). Complements the
// coarse-grained ITracingService (which records one Trace row per request): this service
// records the full span tree, AI-specific context, and powers query/profiling/RCA.
public interface IDistributedTracingService
{
    // --- Span lifecycle ---
    TraceSpan StartSpan(string operationName, string? parentSpanId = null,
        IDictionary<string, object>? attributes = null);
    TraceSpan? EndSpan(string spanId, SpanStatus status = SpanStatus.Ok, string? statusMessage = null);
    void AddEvent(string spanId, string name, IDictionary<string, object>? attributes = null);

    // Record an already-completed generic span with an explicit duration. This is the
    // primitive the AI-specific Record* methods build on (and is handy for backfilling
    // spans whose timing was measured elsewhere).
    TraceSpan RecordSpan(string operationName, string? parentSpanId, long durationMs,
        SpanStatus status = SpanStatus.Ok, IDictionary<string, object>? attributes = null);

    // --- AI-specific spans (start+end recorded in one call) ---
    TraceSpan RecordLlmCall(string? parentSpanId, string model, string prompt, string response,
        int promptTokens, int completionTokens, decimal costUsd, long durationMs, double? temperature = null);
    TraceSpan RecordQualityCheck(string? parentSpanId, double qualityScore, string verdict, long durationMs);
    TraceSpan RecordRetrieval(string? parentSpanId, string query, int docCount, double topScore, long durationMs);
    TraceSpan RecordRoutingDecision(string? parentSpanId, string decision, string reason, long durationMs);
    TraceSpan RecordMcpToolCall(string? parentSpanId, string toolName, string server, string argsJson,
        SpanStatus status, long durationMs);

    // --- Query ---
    IReadOnlyList<TraceSpan> GetTraceSpans(string traceId);
    IReadOnlyList<TraceSpan> QuerySpans(SpanQuery query);
    IReadOnlyList<TraceSummary> ListTraces(int limit = 100);

    // --- Performance profiling ---
    TraceProfile Profile();

    // --- Root cause analysis ---
    TraceRootCauseAnalysis AnalyzeTrace(string traceId);
}

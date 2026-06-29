using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Span-level tracing API: powers the trace explorer, waterfall view, performance
// profiling, and root-cause analysis in the dashboard.
[ApiController]
[Route("api/spans")]
public class SpansController : ControllerBase
{
    private readonly IDistributedTracingService _tracing;

    public SpansController(IDistributedTracingService tracing) => _tracing = tracing;

    // Trace explorer: most recent traces as roll-up summaries.
    [HttpGet("traces")]
    public ActionResult<IReadOnlyList<TraceSummary>> ListTraces([FromQuery] int limit = 100) =>
        Ok(_tracing.ListTraces(limit));

    // Full span tree for one trace (waterfall / span hierarchy view).
    [HttpGet("traces/{traceId}")]
    public ActionResult<IReadOnlyList<TraceSpan>> GetTrace(string traceId)
    {
        var spans = _tracing.GetTraceSpans(traceId);
        return spans.Count == 0 ? NotFound() : Ok(spans);
    }

    // Filterable span search (by operation, duration, status, time range, AI kind).
    [HttpPost("query")]
    public ActionResult<IReadOnlyList<TraceSpan>> Query(SpanQuery query) => Ok(_tracing.QuerySpans(query));

    // Performance profiling: per-operation p50/p95/p99 + slowest traces.
    [HttpGet("profile")]
    public ActionResult<TraceProfile> Profile() => Ok(_tracing.Profile());

    // Root-cause analysis for a single trace.
    [HttpGet("traces/{traceId}/rca")]
    public ActionResult<TraceRootCauseAnalysis> Rca(string traceId) => Ok(_tracing.AnalyzeTrace(traceId));

    // Seed a couple of realistic AI traces (one healthy, one failing) so the UI has data
    // without a live workload. Returns the created trace ids.
    [HttpPost("demo")]
    public ActionResult<object> Seed()
    {
        var ids = new List<string>();

        // --- Healthy chat request: route -> retrieve -> LLM -> quality -> tool ---
        // The root is recorded with the total duration so it encloses its children in the
        // waterfall; children attach to it via root.SpanId.
        var root = _tracing.RecordSpan("Chat Request", null, durationMs: 1060, SpanStatus.Ok);
        _tracing.RecordRoutingDecision(root.SpanId, "claude-opus-4-8", "complex reasoning prompt", 4);
        _tracing.RecordRetrieval(root.SpanId, "platform SLO definitions", docCount: 5, topScore: 0.91, durationMs: 73);
        _tracing.RecordLlmCall(root.SpanId, "claude-opus-4-8",
            prompt: "Summarize the SLO policy.", response: "Availability target is 99.9% over 30 days...",
            promptTokens: 320, completionTokens: 110, costUsd: 0.0042m, durationMs: 880, temperature: 0.2);
        _tracing.RecordQualityCheck(root.SpanId, qualityScore: 0.94, verdict: "Passed", durationMs: 60);
        _tracing.RecordMcpToolCall(root.SpanId, "get_slo_status", "monitoring", "{\"slo\":\"api-availability\"}",
            SpanStatus.Ok, durationMs: 41);
        ids.Add(root.TraceId);

        // --- Failing request: retrieval ok, MCP tool times out -> request fails (for RCA) ---
        var bad = _tracing.RecordSpan("Chat Request", null, durationMs: 6800, SpanStatus.Error,
            new Dictionary<string, object> { ["error"] = "downstream MCP tool 'open_incident' timed out" });
        _tracing.RecordRetrieval(bad.SpanId, "incident playbook", docCount: 2, topScore: 0.44, durationMs: 95);
        _tracing.RecordLlmCall(bad.SpanId, "claude-haiku-4-5",
            prompt: "Open an incident.", response: "Calling incident tool...",
            promptTokens: 80, completionTokens: 30, costUsd: 0.0003m, durationMs: 1450);
        _tracing.RecordMcpToolCall(bad.SpanId, "open_incident", "incident", "{\"sev\":1}",
            SpanStatus.Error, durationMs: 5200);
        ids.Add(bad.TraceId);

        return Ok(new { seeded = ids });
    }
}

using System.Collections.Concurrent;
using System.Diagnostics;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// =============================================================================
// Distributed Tracing Service — OpenTelemetry, AI-aware
// =============================================================================
//
// DESIGN OVERVIEW
// ----------------
// This service produces and queries the *span tree* for every AI request. It plays two
// roles at once:
//
//   1. Instrumentation producer — every span is also created as a System.Diagnostics
//      .Activity via a shared ActivitySource ("AIQuality.Tracing"). OpenTelemetry, wired
//      up in Program.cs, listens to that source and exports spans over OTLP to Jaeger.
//      This is the standard, vendor-neutral .NET tracing path (Activity == OTel span).
//
//   2. Query store — because Jaeger is a *separate* system and we want an in-process,
//      always-available query/profiling/RCA surface for the dashboard, every span is also
//      mirrored into an in-memory store (TraceSpan objects). In production this store is
//      backed by PostgreSQL + TimescaleDB (see notes on ITraceSpanStore below); the
//      in-memory implementation here keeps the service runnable with zero infra.
//
// SAMPLING
// --------
// Two complementary strategies:
//   * Head-based (cheap, decided at span start): configured on the OpenTelemetry pipeline
//     in Program.cs (e.g. ParentBased(TraceIdRatioBased)). It decides whether a span is
//     *exported to Jaeger*.
//   * Tail-based (decided after the trace completes): implemented in code — we ALWAYS keep
//     a trace in the query store if it errored, was slow (> SlowTraceMs), or carries AI
//     context worth inspecting, even when head sampling dropped it for Jaeger. This is why
//     the query store is independent of the export sampler.
//
// CONTEXT PROPAGATION
// -------------------
// Within the process, Activity.Current carries the active span; child spans inherit the
// parent automatically. Across services, the W3C `traceparent` header is propagated by the
// OpenTelemetry ASP.NET Core instrumentation, so a TraceId started upstream continues here.
// =============================================================================
public class TracingService : IDistributedTracingService
{
    // Single shared source — Program.cs registers this exact name with OpenTelemetry.
    public static readonly ActivitySource ActivitySource = new("AIQuality.Tracing", "1.0.0");

    // Query store. Keyed by SpanId; a secondary index groups spans by TraceId.
    private readonly ConcurrentDictionary<string, TraceSpan> _spans = new();
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, byte>> _byTrace = new();
    // Activities for spans that are still open (so EndSpan can stop the right one).
    private readonly ConcurrentDictionary<string, Activity> _openActivities = new();

    // Traces slower than this are always retained by the tail-sampling rule.
    private const long SlowTraceMs = 1000;

    // -------------------------------------------------------------------------
    // Span lifecycle
    // -------------------------------------------------------------------------
    public TraceSpan StartSpan(string operationName, string? parentSpanId = null,
        IDictionary<string, object>? attributes = null)
    {
        // Resolve our logical parent from the provided span id.
        TraceSpan? parent = parentSpanId is not null && _spans.TryGetValue(parentSpanId, out var p) ? p : null;

        // Build an EXPLICIT parent context so our span trees are independent of the ambient
        // ASP.NET request Activity. A root (no parent) starts a brand-new trace; a child
        // inherits its parent's trace/span context. Without this, every span created during
        // one HTTP request would collapse into the request's trace.
        ActivityContext parentContext = default;
        if (parent is not null)
            parentContext = new ActivityContext(
                ActivityTraceId.CreateFromString(parent.TraceId.AsSpan()),
                ActivitySpanId.CreateFromString(parent.SpanId.AsSpan()),
                ActivityTraceFlags.Recorded);

        // Start a real OTel Activity. May be null if no listener sampled it — we still
        // create a TraceSpan so the query store is complete regardless of export sampling.
        // For a ROOT span we detach Activity.Current first: otherwise StartActivity treats a
        // default parentContext as "use the ambient activity" and our root would inherit the
        // incoming HTTP request's trace id. We restore Current afterwards (we nest via
        // explicit parent ids, not the ambient stack).
        var saved = Activity.Current;
        Activity? activity;
        try
        {
            if (parent is null) Activity.Current = null;
            activity = ActivitySource.StartActivity(operationName, ActivityKind.Internal, parentContext);
        }
        finally
        {
            Activity.Current = saved;
        }

        var span = new TraceSpan
        {
            OperationName = operationName,
            // Prefer the Activity's W3C ids; fall back to generated ids when unsampled.
            TraceId = activity?.TraceId.ToString() ?? parent?.TraceId ?? ActivityTraceId.CreateRandom().ToString(),
            SpanId = activity?.SpanId.ToString() ?? ActivitySpanId.CreateRandom().ToString(),
            // Parent linkage comes from our resolved parent only (null => root) so root
            // detection in the query/RCA layer is deterministic.
            ParentSpanId = parent?.SpanId,
            StartTime = DateTimeOffset.UtcNow,
            Status = SpanStatus.Unset,
        };

        if (attributes is not null)
            foreach (var (k, v) in attributes)
            {
                span.Attributes[k] = v;
                activity?.SetTag(k, v);
            }

        Index(span);
        if (activity is not null) _openActivities[span.SpanId] = activity;
        return span;
    }

    public TraceSpan? EndSpan(string spanId, SpanStatus status = SpanStatus.Ok, string? statusMessage = null)
    {
        if (!_spans.TryGetValue(spanId, out var span)) return null;

        span.EndTime = DateTimeOffset.UtcNow;
        span.DurationMs = (long)(span.EndTime.Value - span.StartTime).TotalMilliseconds;
        span.Status = status;
        span.StatusMessage = statusMessage;

        if (_openActivities.TryRemove(spanId, out var activity))
        {
            activity.SetStatus(ToActivityStatus(status), statusMessage);
            activity.Stop(); // hands the span to OpenTelemetry for export (head sampling applies here)
            activity.Dispose();
        }
        return span;
    }

    public void AddEvent(string spanId, string name, IDictionary<string, object>? attributes = null)
    {
        if (!_spans.TryGetValue(spanId, out var span)) return;
        var evt = new SpanEvent { Name = name };
        if (attributes is not null) foreach (var (k, v) in attributes) evt.Attributes[k] = v;
        span.Events.Add(evt);

        if (_openActivities.TryGetValue(spanId, out var activity))
            activity.AddEvent(new ActivityEvent(name));
    }

    // -------------------------------------------------------------------------
    // AI-specific spans — each records a complete (already-finished) span with AIContext.
    // The ai.* tags are what make Jaeger traces legible for LLM workloads, and the
    // AIContext powers the dashboard's LLM/quality/cost panels.
    // -------------------------------------------------------------------------
    public TraceSpan RecordLlmCall(string? parentSpanId, string model, string prompt, string response,
        int promptTokens, int completionTokens, decimal costUsd, long durationMs, double? temperature = null)
    {
        var span = RecordSpan("LLM Call", parentSpanId, durationMs, SpanStatus.Ok);
        span.AIContext = new AIContext
        {
            Kind = "llm_call",
            Model = model,
            Prompt = Truncate(prompt, 2000),
            Response = Truncate(response, 2000),
            PromptTokens = promptTokens,
            CompletionTokens = completionTokens,
            CostUsd = costUsd,
            Temperature = temperature,
        };
        span.Tags["ai.model"] = model;
        span.Attributes["ai.tokens.total"] = promptTokens + completionTokens;
        span.Attributes["ai.cost.usd"] = costUsd;
        return span;
    }

    public TraceSpan RecordQualityCheck(string? parentSpanId, double qualityScore, string verdict, long durationMs)
    {
        var status = verdict.Equals("Failed", StringComparison.OrdinalIgnoreCase) ? SpanStatus.Error : SpanStatus.Ok;
        var span = RecordSpan("Quality Check", parentSpanId, durationMs, status);
        span.AIContext = new AIContext { Kind = "quality_check", QualityScore = qualityScore, QualityVerdict = verdict };
        span.Tags["ai.quality.verdict"] = verdict;
        span.Attributes["ai.quality.score"] = qualityScore;
        return span;
    }

    public TraceSpan RecordRetrieval(string? parentSpanId, string query, int docCount, double topScore, long durationMs)
    {
        var span = RecordSpan("Knowledge Retrieval", parentSpanId, durationMs, SpanStatus.Ok);
        span.AIContext = new AIContext
        {
            Kind = "retrieval", RetrievalQuery = Truncate(query, 500), RetrievedDocCount = docCount, TopScore = topScore,
        };
        span.Attributes["ai.retrieval.docs"] = docCount;
        return span;
    }

    public TraceSpan RecordRoutingDecision(string? parentSpanId, string decision, string reason, long durationMs)
    {
        var span = RecordSpan("Model Routing", parentSpanId, durationMs, SpanStatus.Ok);
        span.AIContext = new AIContext { Kind = "routing", RoutingDecision = decision, RoutingReason = reason };
        span.Tags["ai.route"] = decision;
        return span;
    }

    public TraceSpan RecordMcpToolCall(string? parentSpanId, string toolName, string server, string argsJson,
        SpanStatus status, long durationMs)
    {
        var span = RecordSpan($"MCP Tool: {toolName}", parentSpanId, durationMs, status);
        span.AIContext = new AIContext
        {
            Kind = "mcp_tool_call", ToolName = toolName, ToolServer = server, ToolArgsJson = Truncate(argsJson, 1000),
        };
        span.Tags["mcp.tool"] = toolName;
        span.Tags["mcp.server"] = server;
        return span;
    }

    // -------------------------------------------------------------------------
    // Query
    // -------------------------------------------------------------------------
    public IReadOnlyList<TraceSpan> GetTraceSpans(string traceId)
    {
        if (!_byTrace.TryGetValue(traceId, out var ids)) return Array.Empty<TraceSpan>();
        return ids.Keys.Select(id => _spans[id]).OrderBy(s => s.StartTime).ToList();
    }

    public IReadOnlyList<TraceSpan> QuerySpans(SpanQuery q)
    {
        IEnumerable<TraceSpan> result = _spans.Values;
        if (q.TraceId is not null) result = result.Where(s => s.TraceId == q.TraceId);
        if (q.Operation is not null) result = result.Where(s => s.OperationName.Contains(q.Operation, StringComparison.OrdinalIgnoreCase));
        if (q.MinDurationMs is not null) result = result.Where(s => s.DurationMs >= q.MinDurationMs);
        if (q.Status is not null) result = result.Where(s => s.Status == q.Status);
        if (q.Since is not null) result = result.Where(s => s.StartTime >= q.Since);
        if (q.Until is not null) result = result.Where(s => s.StartTime <= q.Until);
        if (q.AIKind is not null) result = result.Where(s => s.AIContext?.Kind == q.AIKind);
        return result.OrderByDescending(s => s.StartTime).Take(q.Limit).ToList();
    }

    public IReadOnlyList<TraceSummary> ListTraces(int limit = 100) =>
        _byTrace.Keys.Select(Summarize).Where(s => s is not null).Cast<TraceSummary>()
            .OrderByDescending(s => s.StartTime).Take(limit).ToList();

    // -------------------------------------------------------------------------
    // Performance profiling — per-operation latency percentiles + slowest traces.
    // The query equivalents in TimescaleDB would be continuous aggregates over the spans
    // hypertable (e.g. percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) ... ).
    // -------------------------------------------------------------------------
    public TraceProfile Profile()
    {
        var ops = _spans.Values
            .Where(s => s.EndTime is not null)
            .GroupBy(s => s.OperationName)
            .Select(g =>
            {
                var durations = g.Select(s => s.DurationMs).OrderBy(d => d).ToList();
                return new OperationProfile
                {
                    Operation = g.Key,
                    Count = durations.Count,
                    P50Ms = Percentile(durations, 0.50),
                    P95Ms = Percentile(durations, 0.95),
                    P99Ms = Percentile(durations, 0.99),
                    MaxMs = durations[^1],
                    ErrorRate = g.Count(s => s.Status == SpanStatus.Error) / (double)g.Count(),
                };
            })
            .OrderByDescending(o => o.P95Ms)
            .ToList();

        var slowest = _byTrace.Keys.Select(Summarize).Where(s => s is not null).Cast<TraceSummary>()
            .OrderByDescending(s => s.DurationMs).Take(10).ToList();

        return new TraceProfile { Operations = ops, SlowestTraces = slowest, TotalSpans = _spans.Count };
    }

    // -------------------------------------------------------------------------
    // Root cause analysis — local, per-trace heuristics. Three lenses:
    //   * Failure patterns   — the first errored span (deepest cause) in the tree.
    //   * Performance bottleneck — the span owning the largest share of self-time.
    //   * Dependency analysis — error in a child propagating to its parent.
    // The Python automated-rca service does the heavier cross-trace correlation; this gives
    // the UI an instant, explainable first answer.
    // -------------------------------------------------------------------------
    public TraceRootCauseAnalysis AnalyzeTrace(string traceId)
    {
        var spans = GetTraceSpans(traceId);
        var findings = new List<RcaFinding>();
        if (spans.Count == 0)
            return new TraceRootCauseAnalysis { TraceId = traceId, Status = SpanStatus.Unset, Findings = findings };

        var byId = spans.ToDictionary(s => s.SpanId);
        var root = spans.FirstOrDefault(s => s.ParentSpanId is null) ?? spans[0];
        var overallStatus = spans.Any(s => s.Status == SpanStatus.Error) ? SpanStatus.Error : root.Status;

        // 1) Failure pattern: the ORIGINATING failure, not a propagated one. Parent/root spans
        //    are typically marked Error because a child failed; the true cause is the deepest
        //    error — an error span that has no errored span among its ancestors.
        var errorSpans = spans.Where(s => s.Status == SpanStatus.Error).ToList();
        var ancestorsOfErrors = new HashSet<string>();
        foreach (var e in errorSpans)
        {
            var pid = e.ParentSpanId;
            while (pid is not null && byId.TryGetValue(pid, out var par))
            {
                ancestorsOfErrors.Add(pid);
                pid = par.ParentSpanId;
            }
        }
        var originating = errorSpans
            .Where(s => !ancestorsOfErrors.Contains(s.SpanId)) // exclude spans that merely propagated a child's error
            .OrderBy(s => s.StartTime)
            .FirstOrDefault();

        string? primary = null;
        if (originating is not null)
        {
            primary = originating.SpanId;
            findings.Add(new RcaFinding
            {
                Category = "failure", Severity = "critical",
                SpanId = originating.SpanId, Operation = originating.OperationName,
                Description = $"'{originating.OperationName}' failed: {originating.StatusMessage ?? "no detail"}.",
                Recommendation = "Inspect this span's events/attributes; it is the originating failure in the trace.",
            });
        }

        // 2) Performance bottleneck: span with the most self-time (excludes child time).
        var bottleneck = spans.OrderByDescending(SelfTime).First();
        if (SelfTime(bottleneck) > 0 && bottleneck.DurationMs >= SlowTraceMs / 2)
            findings.Add(new RcaFinding
            {
                Category = "bottleneck", Severity = "warning",
                SpanId = bottleneck.SpanId, Operation = bottleneck.OperationName,
                Description = $"'{bottleneck.OperationName}' accounts for {SelfTime(bottleneck)} ms of self-time.",
                Recommendation = bottleneck.AIContext?.Kind == "llm_call"
                    ? "Consider a faster model, shorter prompt, or streaming for this LLM call."
                    : "Profile this operation; it dominates the trace latency.",
            });

        // 3) Dependency analysis: a failing child that fails its parent.
        foreach (var child in spans.Where(s => s.Status == SpanStatus.Error && s.ParentSpanId is not null))
        {
            var parent = spans.FirstOrDefault(s => s.SpanId == child.ParentSpanId);
            if (parent is not null && parent.Status == SpanStatus.Error)
                findings.Add(new RcaFinding
                {
                    Category = "dependency", Severity = "warning",
                    SpanId = child.SpanId, Operation = child.OperationName,
                    Description = $"Failure in '{child.OperationName}' propagated to parent '{parent.OperationName}'.",
                    Recommendation = "Add a fallback/retry or circuit breaker around this dependency.",
                });
        }

        return new TraceRootCauseAnalysis
        {
            TraceId = traceId, Status = overallStatus, PrimaryRootCauseSpanId = primary, Findings = findings,
        };
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------
    public TraceSpan RecordSpan(string operationName, string? parentSpanId, long durationMs,
        SpanStatus status = SpanStatus.Ok, IDictionary<string, object>? attributes = null)
    {
        var span = StartSpan(operationName, parentSpanId, attributes);
        // Back-date the start so the span's bar reflects the measured duration even though
        // no real wall-clock time elapsed (the timing was measured by the caller).
        var end = DateTimeOffset.UtcNow;
        span.StartTime = end.AddMilliseconds(-durationMs);
        span.EndTime = end;
        span.DurationMs = durationMs;
        span.Status = status;

        if (_openActivities.TryRemove(span.SpanId, out var activity))
        {
            activity.SetStatus(ToActivityStatus(status));
            activity.Stop();
            activity.Dispose();
        }
        return span;
    }

    private void Index(TraceSpan span)
    {
        _spans[span.SpanId] = span;
        _byTrace.GetOrAdd(span.TraceId, _ => new ConcurrentDictionary<string, byte>())[span.SpanId] = 0;
    }

    // Self-time = own duration minus time spent in direct children (parallel-safe lower bound).
    private long SelfTime(TraceSpan span)
    {
        var children = _spans.Values.Where(s => s.ParentSpanId == span.SpanId).Sum(s => s.DurationMs);
        return Math.Max(0, span.DurationMs - children);
    }

    private TraceSummary? Summarize(string traceId)
    {
        var spans = GetTraceSpans(traceId);
        if (spans.Count == 0) return null;
        var root = spans.FirstOrDefault(s => s.ParentSpanId is null) ?? spans[0];
        return new TraceSummary
        {
            TraceId = traceId,
            RootOperation = root.OperationName,
            StartTime = spans.Min(s => s.StartTime),
            DurationMs = root.DurationMs > 0 ? root.DurationMs
                : (long)(spans.Max(s => s.EndTime ?? s.StartTime) - spans.Min(s => s.StartTime)).TotalMilliseconds,
            SpanCount = spans.Count,
            Status = spans.Any(s => s.Status == SpanStatus.Error) ? SpanStatus.Error : root.Status,
            TotalCostUsd = spans.Sum(s => s.AIContext?.CostUsd ?? 0m),
            TotalTokens = spans.Sum(s => s.AIContext?.TotalTokens ?? 0),
        };
    }

    private static long Percentile(IReadOnlyList<long> sorted, double p)
    {
        if (sorted.Count == 0) return 0;
        var rank = (int)Math.Ceiling(p * sorted.Count) - 1;
        return sorted[Math.Clamp(rank, 0, sorted.Count - 1)];
    }

    private static ActivityStatusCode ToActivityStatus(SpanStatus s) => s switch
    {
        SpanStatus.Ok => ActivityStatusCode.Ok,
        SpanStatus.Error => ActivityStatusCode.Error,
        _ => ActivityStatusCode.Unset,
    };

    private static string Truncate(string? s, int max) =>
        string.IsNullOrEmpty(s) ? string.Empty : s.Length <= max ? s : s[..max] + "…";
}

using System.Linq;
using AIQuality.API.Services;
using AIQuality.Core.Enums;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class DistributedTracingServiceTests
{
    [Fact]
    public void Each_root_span_starts_an_independent_trace()
    {
        var svc = new TracingService();

        var a = svc.RecordSpan("Request A", null, 100, SpanStatus.Ok);
        var b = svc.RecordSpan("Request B", null, 100, SpanStatus.Ok);

        Assert.NotEqual(a.TraceId, b.TraceId);
        Assert.Null(a.ParentSpanId);
        Assert.Equal(2, svc.ListTraces().Count);
    }

    [Fact]
    public void Child_span_inherits_trace_and_links_to_parent()
    {
        var svc = new TracingService();
        var root = svc.RecordSpan("Chat Request", null, 500, SpanStatus.Ok);

        var child = svc.RecordLlmCall(root.SpanId, "claude-opus-4-8", "p", "r", 10, 20, 0.001m, 200);

        Assert.Equal(root.TraceId, child.TraceId);
        Assert.Equal(root.SpanId, child.ParentSpanId);
        Assert.Equal("llm_call", child.AIContext!.Kind);
        Assert.Equal(30, child.AIContext.TotalTokens);
        Assert.Equal(2, svc.GetTraceSpans(root.TraceId).Count);
    }

    [Fact]
    public void Rca_identifies_failure_bottleneck_and_dependency()
    {
        var svc = new TracingService();
        var root = svc.RecordSpan("Chat Request", null, 6000, SpanStatus.Error);
        svc.RecordRetrieval(root.SpanId, "q", 2, 0.4, 95);
        svc.RecordMcpToolCall(root.SpanId, "open_incident", "incident", "{}", SpanStatus.Error, 5200);

        var rca = svc.AnalyzeTrace(root.TraceId);

        Assert.Equal(SpanStatus.Error, rca.Status);
        Assert.Contains(rca.Findings, f => f.Category == "failure");
        Assert.Contains(rca.Findings, f => f.Category == "bottleneck");
        Assert.Contains(rca.Findings, f => f.Category == "dependency");
        // The earliest error (the MCP tool) is the primary root cause.
        var tool = svc.GetTraceSpans(root.TraceId).First(s => s.OperationName.Contains("open_incident"));
        Assert.Equal(tool.SpanId, rca.PrimaryRootCauseSpanId);
    }

    [Fact]
    public void Profile_reports_percentiles_per_operation()
    {
        var svc = new TracingService();
        foreach (var d in new long[] { 100, 200, 300, 400, 500 })
            svc.RecordSpan("LLM Call", null, d, SpanStatus.Ok);

        var op = svc.Profile().Operations.Single(o => o.Operation == "LLM Call");

        Assert.Equal(5, op.Count);
        Assert.Equal(500, op.MaxMs);
        Assert.True(op.P95Ms >= op.P50Ms);
        Assert.Equal(0, op.ErrorRate);
    }

    [Fact]
    public void Query_filters_by_ai_kind_and_duration()
    {
        var svc = new TracingService();
        var root = svc.RecordSpan("Chat Request", null, 1000, SpanStatus.Ok);
        svc.RecordLlmCall(root.SpanId, "m", "p", "r", 1, 1, 0m, 900);
        svc.RecordQualityCheck(root.SpanId, 0.9, "Passed", 30);

        var llmOnly = svc.QuerySpans(new Core.Entities.SpanQuery { AIKind = "llm_call" });
        var slow = svc.QuerySpans(new Core.Entities.SpanQuery { MinDurationMs = 800 });

        Assert.Single(llmOnly);
        Assert.All(slow, s => Assert.True(s.DurationMs >= 800));
    }
}

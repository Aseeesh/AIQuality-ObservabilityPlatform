using System;
using System.Threading.Tasks;
using AIQuality.Core.Enums;
using AIQuality.Infrastructure.Data;
using AIQuality.Infrastructure.Services;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class TracingServiceTests
{
    private static ApplicationDbContext NewDb() =>
        new(new DbContextOptionsBuilder<ApplicationDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options);

    [Fact]
    public async Task StartTrace_persists_running_trace()
    {
        var svc = new TracingService(NewDb());

        var trace = await svc.StartTraceAsync("chat", "claude-opus-4-8");

        Assert.Equal(TraceStatus.Running, trace.Status);
        Assert.Equal("claude-opus-4-8", trace.Model);
        Assert.NotEqual(Guid.Empty, trace.Id);
    }

    [Fact]
    public async Task CompleteTrace_sets_duration_score_and_status()
    {
        var db = NewDb();
        var svc = new TracingService(db);
        var started = await svc.StartTraceAsync("chat", "claude-opus-4-8");

        var done = await svc.CompleteTraceAsync(started.Id, durationMs: 842, qualityScore: 0.93);

        Assert.NotNull(done);
        Assert.Equal(TraceStatus.Completed, done!.Status);
        Assert.Equal(842, done.DurationMs);
        Assert.Equal(0.93, done.QualityScore);
        Assert.NotNull(done.EndedAt);
    }

    [Fact]
    public async Task CompleteTrace_returns_null_for_unknown_id()
    {
        var svc = new TracingService(NewDb());
        Assert.Null(await svc.CompleteTraceAsync(Guid.NewGuid(), 1, null));
    }

    [Fact]
    public async Task ListTraces_returns_all_started()
    {
        var db = NewDb();
        var svc = new TracingService(db);
        await svc.StartTraceAsync("a", "m1");
        await svc.StartTraceAsync("b", "m2");

        var all = await svc.ListTracesAsync();
        Assert.Equal(2, all.Count);
    }
}

using System.Linq;
using System.Threading.Tasks;
using AIQuality.API.Services;
using AIQuality.Core.Enums;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class SLOServiceTests
{
    [Fact]
    public void Seeds_default_slos()
    {
        var svc = new SLOService();
        var names = svc.Definitions().Select(d => d.SLOName).ToList();
        Assert.Contains("api-availability", names);
        Assert.Contains("eval-latency", names);
        Assert.Contains("quality-score", names);
    }

    [Fact]
    public void Healthy_sli_when_all_good()
    {
        var svc = new SLOService();
        for (int i = 0; i < 100; i++) svc.RecordObservation("quality-score", 0.9); // >= 0.8 => good
        var result = svc.Evaluate("quality-score")!;
        Assert.Equal(SLIStatus.Healthy, result.Status);
        Assert.Equal(1.0, result.Sli);
        Assert.True(result.ErrorBudget.Remaining > 0.99);
    }

    [Fact]
    public void Breached_sli_and_budget_burn_when_many_bad()
    {
        var svc = new SLOService();
        // 30% of events breach the 2000ms latency boundary -> far below the 99% target.
        for (int i = 0; i < 100; i++) svc.RecordObservation("eval-latency", i % 10 < 3 ? 4000 : 500);
        var result = svc.Evaluate("eval-latency")!;
        Assert.Equal(SLIStatus.Breached, result.Status);
        Assert.True(result.ErrorBudget.Consumed > 1);       // over budget
        Assert.Contains(result.ErrorBudget.Alerts, a => a.Contains("burn") || a.Contains("exhausted"));
    }

    [Fact]
    public void Observation_comparison_respects_direction()
    {
        var svc = new SLOService();
        svc.RecordObservation("api-availability", 1); // Gte 1 => good
        svc.RecordObservation("api-availability", 0); // bad
        var r = svc.Evaluate("api-availability")!;
        Assert.Equal(0.5, r.Sli);
        Assert.Equal(2, r.Sampled);
    }

    [Fact]
    public async Task TrackMetrics_and_report()
    {
        var svc = new SLOService();
        for (int i = 0; i < 50; i++) svc.RecordObservation("quality-score", 0.9);
        var metrics = await svc.TrackSLOMetricsAsync();
        Assert.Equal(3, metrics.Total);
        Assert.True(metrics.Compliant >= 1);
        var report = svc.GenerateReport();
        Assert.Contains("SLO Compliance", report.ExecutiveSummary);
    }
}

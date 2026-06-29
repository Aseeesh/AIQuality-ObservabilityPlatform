using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AIQuality.API.Services;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class EvaluationServiceTests
{
    private const string Context =
        "API availability target is 99.9 percent over a 30 day window using error budgets and burn rate.";

    private static EvaluationService NewService() => new(new HeuristicOutputEvaluator());

    private static BatchEvaluationRequest Batch(string env, Func<int, string> output, int n = 6, string dataset = "ds") =>
        new()
        {
            Dataset = dataset,
            Environment = env,
            RubricSet = "quality",
            Items = Enumerable.Range(0, n).Select(i => new EvaluationItem
            {
                Prompt = "Describe the API availability SLO.",
                Context = Context,
                Output = output(i),
                References = new List<string> { "https://docs/slo" },
            }).ToList(),
        };

    private static string GoodOutput(int i) =>
        $"The API availability target is 99.9 percent measured over a rolling 30 day window number {i}, " +
        "tracked using error budgets and burn rate alerts that page the team.";

    [Fact]
    public async Task Batch_aggregates_items_in_parallel()
    {
        var svc = NewService();
        var result = await svc.RunBatchEvaluationAsync(Batch("dev", GoodOutput));

        Assert.Equal(6, result.Run.ItemCount);
        Assert.Equal(6, result.Items.Count);
        Assert.True(result.Run.Overall > 0);
        Assert.Contains("accuracy", result.PerRubric.Keys);
        Assert.True(result.Run.P95LatencyMs >= result.Run.MeanLatencyMs);
    }

    [Fact]
    public async Task Good_outputs_pass_gates_in_dev()
    {
        var svc = NewService();
        var result = await svc.RunBatchEvaluationAsync(Batch("dev", GoodOutput));
        Assert.NotEqual(QualityGateStatus.Failed, result.Run.GateStatus);
        Assert.All(result.Gates, g => Assert.Equal(g.Name == "safety" ? QualityGateStatus.Passed : g.Status, g.Status));
    }

    [Fact]
    public async Task Unsafe_output_fails_safety_gate()
    {
        var svc = NewService();
        var result = await svc.RunBatchEvaluationAsync(Batch("prod", _ => "We should attack and bomb the server."));
        var safety = result.Gates.Single(g => g.Name == "safety");
        Assert.Equal(QualityGateStatus.Failed, safety.Status);
        Assert.Equal(QualityGateStatus.Failed, result.Run.GateStatus);
    }

    [Fact]
    public async Task Regression_detected_between_baseline_and_degraded_run()
    {
        var svc = NewService();
        await svc.RunBatchEvaluationAsync(Batch("staging", GoodOutput, dataset: "reg"));
        var degraded = await svc.RunBatchEvaluationAsync(
            Batch("staging", i => i % 2 == 0 ? "Bad." : "It uses budgets.", dataset: "reg"));

        Assert.NotNull(degraded.Regression);
        Assert.True(degraded.Regression!.HasBaseline);
        Assert.True(degraded.Regression.ScoreDelta < 0);
        Assert.True(degraded.Regression.Significant);
        Assert.True(degraded.Regression.Degraded);
        Assert.NotEmpty(degraded.Regression.Alerts);
    }

    [Fact]
    public async Task First_run_has_no_baseline()
    {
        var svc = NewService();
        var result = await svc.RunBatchEvaluationAsync(Batch("dev", GoodOutput, dataset: "fresh"));
        Assert.False(result.Regression!.HasBaseline);
    }

    [Fact]
    public async Task History_and_report_are_available_after_run()
    {
        var svc = NewService();
        var result = await svc.RunBatchEvaluationAsync(Batch("dev", GoodOutput, dataset: "hist"));

        Assert.Contains(svc.History("hist"), r => r.Id == result.Run.Id);
        var fetched = svc.GetResult(result.Run.Id);
        Assert.NotNull(fetched);
        var report = svc.GenerateReport(fetched!);
        Assert.Contains("Evaluation:", report.ExecutiveSummary);
        Assert.Equal(result.Run.Id, report.Run.Id);
    }

    [Fact]
    public async Task Prod_gates_are_stricter_than_dev()
    {
        var svc = NewService();
        // Mediocre outputs: pass loose dev quality gate but fail strict prod min-quality.
        var mediocre = Batch("dev", _ => "Availability is around ninety nine percent over a month.");
        var dev = await svc.RunBatchEvaluationAsync(mediocre);

        var prodGates = svc.EvaluateGates(dev.Run, dev.PerRubric, "prod");
        var devQuality = dev.Gates.Single(g => g.Name == "min-quality");
        var prodQuality = prodGates.Single(g => g.Name == "min-quality");
        Assert.True(prodQuality.Threshold > devQuality.Threshold);
    }
}

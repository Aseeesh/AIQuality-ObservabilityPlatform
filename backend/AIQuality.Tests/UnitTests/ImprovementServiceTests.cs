using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AIQuality.API.Services;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class ImprovementServiceTests
{
    private const string Ctx =
        "API availability target is 99.9 percent over a 30 day window using error budgets and burn rate.";

    private static (EvaluationService eval, ImprovementService imp) NewServices()
    {
        var eval = new EvaluationService(new HeuristicOutputEvaluator());
        return (eval, new ImprovementService(eval));
    }

    private static BatchEvaluationRequest Batch(string env, System.Func<int, string> output, string dataset) => new()
    {
        Dataset = dataset,
        Environment = env,
        RubricSet = "quality",
        Items = Enumerable.Range(0, 6).Select(i => new EvaluationItem
        {
            Prompt = "Describe the API availability SLO.", Context = Ctx, Output = output(i),
        }).ToList(),
    };

    [Fact]
    public void Analyze_reports_no_data_without_runs()
    {
        var (_, imp) = NewServices();
        var a = imp.AnalyzeQuality(new ImprovementRequest { Dataset = "none", Environment = "staging" });
        Assert.False(a.HasData);
    }

    [Fact]
    public async Task Plan_identifies_quality_gaps_and_orders_by_priority()
    {
        var (eval, imp) = NewServices();
        // Weak outputs -> quality gaps below the 0.85 target.
        await eval.RunBatchEvaluationAsync(Batch("staging", _ => "It is around ninety percent.", "ds"));

        var plan = await imp.GenerateImprovementPlanAsync(new ImprovementRequest
        {
            Dataset = "ds", Environment = "staging", TargetQuality = 0.85, UserSatisfaction = 0.5,
        });

        Assert.True(plan.Analysis.HasData);
        Assert.NotEmpty(plan.Analysis.QualityGaps);
        Assert.NotEmpty(plan.Opportunities);
        // Ordered by descending priority.
        var priorities = plan.Opportunities.Select(o => o.Priority).ToList();
        Assert.Equal(priorities.OrderByDescending(p => p).ToList(), priorities);
        // Low satisfaction yields a prompt opportunity.
        Assert.Contains(plan.Opportunities, o => o.Area == ImprovementArea.Prompt);
    }

    [Fact]
    public async Task Plan_designs_canary_experiment_for_top_opportunity()
    {
        var (eval, imp) = NewServices();
        await eval.RunBatchEvaluationAsync(Batch("staging", _ => "Bad.", "ds2"));

        var plan = await imp.GenerateImprovementPlanAsync(new ImprovementRequest
        {
            Dataset = "ds2", Environment = "staging", TargetQuality = 0.85,
        });

        Assert.NotNull(plan.Experiment);
        var exp = plan.Experiment!;
        Assert.Equal(4, exp.CanaryStages.Count);
        Assert.Equal(100, exp.CanaryStages.Last().TrafficPercent);
        Assert.InRange(exp.MinSamplesPerArm, 50, 5000);
        Assert.Contains("safety", exp.GuardrailMetrics);
        Assert.NotEmpty(exp.ValidationSteps);
    }

    [Fact]
    public async Task Declining_trend_adds_regression_opportunity()
    {
        var (eval, imp) = NewServices();
        // First run good, second run worse -> declining trend on the same dataset/env.
        await eval.RunBatchEvaluationAsync(Batch("staging", _ =>
            "The API availability target is 99.9 percent over a rolling 30 day window using error budgets and burn rate alerts.",
            "trend"));
        await eval.RunBatchEvaluationAsync(Batch("staging", _ => "Bad.", "trend"));

        var plan = await imp.GenerateImprovementPlanAsync(new ImprovementRequest
        {
            Dataset = "trend", Environment = "staging", TargetQuality = 0.85,
        });

        Assert.Equal("declining", plan.Analysis.Trend);
        Assert.Contains(plan.Opportunities, o => o.Title.Contains("regression"));
    }
}

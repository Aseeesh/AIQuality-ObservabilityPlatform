using AIQuality.Core.Entities;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Generate model-improvement plans from evaluation history.
[ApiController]
[Route("api/improvement")]
public class ImprovementController : ControllerBase
{
    private readonly IImprovementService _improvement;
    private readonly IEvaluationService _eval;

    public ImprovementController(IImprovementService improvement, IEvaluationService eval)
    {
        _improvement = improvement;
        _eval = eval;
    }

    // Generate a prioritised improvement plan + experiment design.
    [HttpPost("plan")]
    public async Task<ActionResult<ImprovementPlan>> Plan(ImprovementRequest request, CancellationToken ct)
        => Ok(await _improvement.GenerateImprovementPlanAsync(request, ct));

    // Just the quality analysis (trend, gaps, cost, latency).
    [HttpPost("analyze")]
    public ActionResult<QualityAnalysis> Analyze(ImprovementRequest request)
        => Ok(_improvement.AnalyzeQuality(request));

    // Seed an evaluation run with quality gaps, then generate a plan against it.
    [HttpPost("demo")]
    public async Task<ActionResult<ImprovementPlan>> Demo(CancellationToken ct)
    {
        var ctx = "API availability target is 99.9 percent over a 30 day window using error budgets.";
        var request = new BatchEvaluationRequest
        {
            Dataset = "improve-demo",
            Environment = "staging",
            RubricSet = "quality",
            Items = Enumerable.Range(0, 6).Select(i => new EvaluationItem
            {
                Prompt = "Describe the API availability SLO.",
                Context = ctx,
                Output = i % 2 == 0 ? "It is around ninety percent." : "Availability is good.",
            }).ToList(),
        };
        await _eval.RunBatchEvaluationAsync(request, ct);

        var plan = await _improvement.GenerateImprovementPlanAsync(new ImprovementRequest
        {
            Dataset = "improve-demo", Environment = "staging",
            TargetQuality = 0.85, UserSatisfaction = 0.55,
        }, ct);
        return Ok(plan);
    }
}

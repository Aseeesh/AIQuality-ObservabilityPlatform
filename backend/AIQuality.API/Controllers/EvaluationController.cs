using AIQuality.Core.Entities;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Trigger and query batch evaluations and quality gates.
[ApiController]
[Route("api/evaluation")]
public class EvaluationController : ControllerBase
{
    private readonly IEvaluationService _eval;

    public EvaluationController(IEvaluationService eval) => _eval = eval;

    // Trigger-based evaluation: run a batch and return the full result (run + gates + regression).
    [HttpPost("batch")]
    public async Task<ActionResult<BatchEvaluationResult>> RunBatch(BatchEvaluationRequest request, CancellationToken ct)
        => Ok(await _eval.RunBatchEvaluationAsync(request, ct));

    // CI/CD gate: 200 when gates pass (or only warn), 422 when a gate fails — so a pipeline
    // step can simply check the HTTP status to pass/fail the build.
    [HttpPost("ci-gate")]
    public async Task<ActionResult<BatchEvaluationResult>> CiGate(BatchEvaluationRequest request, CancellationToken ct)
    {
        var result = await _eval.RunCiCdGateAsync(request, ct);
        return result.Run.GateStatus == Core.Enums.QualityGateStatus.Failed
            ? UnprocessableEntity(result)
            : Ok(result);
    }

    // Run history (optionally filtered by dataset).
    [HttpGet("runs")]
    public ActionResult<IReadOnlyList<EvaluationRun>> Runs([FromQuery] string? dataset)
        => Ok(_eval.History(dataset));

    // Report for a stored run.
    [HttpGet("runs/{id:guid}/report")]
    public ActionResult<EvaluationReport> Report(Guid id)
    {
        var result = _eval.GetResult(id);
        return result is null ? NotFound() : Ok(_eval.GenerateReport(result));
    }

    // Seed two runs on the same dataset (a healthy baseline then a degraded run) to
    // demonstrate aggregation, gates, and statistically-significant regression detection.
    [HttpPost("demo")]
    public async Task<ActionResult<object>> Seed(CancellationToken ct)
    {
        var context = "API availability target is 99.9 percent over a 30 day window using error budgets and burn rate.";

        BatchEvaluationRequest Build(Func<int, string> output) => new()
        {
            Dataset = "demo-suite",
            Environment = "staging",
            RubricSet = "quality",
            Items = Enumerable.Range(0, 6).Select(i => new EvaluationItem
            {
                Prompt = "Describe the API availability SLO.",
                Context = context,
                Output = output(i),
                References = new List<string> { "https://docs.aiquality/slo" },
            }).ToList(),
        };

        // Baseline: grounded, complete answers.
        var baseline = await _eval.RunBatchEvaluationAsync(Build(_ =>
            "The API availability target is 99.9 percent measured over a rolling 30 day window, " +
            "tracked using error budgets and burn rate alerts."), ct);

        // Regressed: terse, partly ungrounded answers (lower accuracy/completeness).
        var regressed = await _eval.RunCiCdGateAsync(Build(i =>
            i % 2 == 0 ? "Availability is good." : "It uses budgets."), ct);

        return Ok(new
        {
            baselineRunId = baseline.Run.Id,
            regressedRunId = regressed.Run.Id,
            regressedGateStatus = regressed.Run.GateStatus.ToString(),
            regression = regressed.Regression,
        });
    }
}

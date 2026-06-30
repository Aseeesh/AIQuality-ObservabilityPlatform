using AIQuality.Core.Entities;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Manage SLO definitions and report SLI compliance / error-budget burn.
[ApiController]
[Route("api/slo")]
public class SLOController : ControllerBase
{
    private readonly ISLOService _slo;

    public SLOController(ISLOService slo) => _slo = slo;

    // Full SLO compliance snapshot.
    [HttpGet]
    public async Task<ActionResult<SLOMetrics>> Metrics(CancellationToken ct) =>
        Ok(await _slo.TrackSLOMetricsAsync(ct));

    [HttpGet("definitions")]
    public ActionResult<IReadOnlyList<SLODefinition>> Definitions() => Ok(_slo.Definitions());

    [HttpPost("definitions")]
    public ActionResult<SLODefinition> Define(SLODefinition definition) => Ok(_slo.Define(definition));

    [HttpGet("{name}")]
    public ActionResult<SLOComplianceResult> Get(string name)
    {
        var result = _slo.Evaluate(name);
        return result is null ? NotFound() : Ok(result);
    }

    // Record a raw observation (converted to good/bad by the SLO definition).
    [HttpPost("{name}/observe")]
    public IActionResult Observe(string name, [FromQuery] double value)
    {
        _slo.RecordObservation(name, value);
        return Ok(_slo.Evaluate(name));
    }

    [HttpGet("report")]
    public ActionResult<SLOReport> Report() => Ok(_slo.GenerateReport());

    // Seed realistic SLI data (one healthy SLO, one burning its budget) for the dashboard.
    [HttpPost("demo")]
    public ActionResult<SLOMetrics> Demo()
    {
        var rng = new Random(7);
        for (int i = 0; i < 200; i++)
        {
            _slo.RecordObservation("api-availability", rng.NextDouble() < 0.9995 ? 1 : 0);
            // eval-latency: ~6% of requests breach the 2000ms budget => burns the 1% budget fast.
            _slo.RecordObservation("eval-latency", rng.NextDouble() < 0.94 ? 800 : 3500);
            _slo.RecordObservation("quality-score", rng.NextDouble() < 0.96 ? 0.9 : 0.5);
        }
        return Ok(_slo.TrackSLOMetricsAsync().GetAwaiter().GetResult());
    }
}

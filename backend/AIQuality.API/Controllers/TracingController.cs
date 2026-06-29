using AIQuality.API.Models;
using AIQuality.Core.Entities;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Ingest and query distributed traces/spans for AI requests.
[ApiController]
[Route("api/tracing")]
public class TracingController : ControllerBase
{
    private readonly ITracingService _tracing;

    public TracingController(ITracingService tracing) => _tracing = tracing;

    // List all traces, most recent first.
    [HttpGet]
    public async Task<ActionResult<IReadOnlyList<Trace>>> List(CancellationToken ct) =>
        Ok(await _tracing.ListTracesAsync(ct));

    // Fetch a single trace by id.
    [HttpGet("{id:guid}")]
    public async Task<ActionResult<Trace>> Get(Guid id, CancellationToken ct)
    {
        var trace = await _tracing.GetTraceAsync(id, ct);
        return trace is null ? NotFound() : Ok(trace);
    }

    // Start a new trace for a model invocation.
    [HttpPost]
    public async Task<ActionResult<Trace>> Start(StartTraceRequest req, CancellationToken ct)
    {
        var trace = await _tracing.StartTraceAsync(req.Name, req.Model, ct);
        return CreatedAtAction(nameof(Get), new { id = trace.Id }, trace);
    }

    // Complete a running trace, optionally attaching a quality score.
    [HttpPost("{id:guid}/complete")]
    public async Task<ActionResult<Trace>> Complete(Guid id, CompleteTraceRequest req, CancellationToken ct)
    {
        var trace = await _tracing.CompleteTraceAsync(id, req.DurationMs, req.QualityScore, ct);
        return trace is null ? NotFound() : Ok(trace);
    }
}

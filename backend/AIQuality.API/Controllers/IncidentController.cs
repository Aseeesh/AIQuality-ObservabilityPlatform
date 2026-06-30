using AIQuality.API.Models;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;
using Microsoft.AspNetCore.Mvc;

namespace AIQuality.API.Controllers;

// Create, track, and resolve incidents; generate post-mortems.
[ApiController]
[Route("api/incidents")]
public class IncidentController : ControllerBase
{
    private readonly IIncidentService _incidents;
    private readonly IDistributedTracingService _tracing;

    public IncidentController(IIncidentService incidents, IDistributedTracingService tracing)
    {
        _incidents = incidents;
        _tracing = tracing;
    }

    [HttpPost]
    public async Task<ActionResult<IncidentView>> Create(IncidentRequest request, CancellationToken ct)
        => Ok(await _incidents.CreateIncidentAsync(request, ct));

    [HttpGet]
    public ActionResult<IReadOnlyList<Incident>> Active() => Ok(_incidents.Active());

    [HttpGet("{id:guid}")]
    public ActionResult<IncidentView> Get(Guid id)
    {
        var view = _incidents.Get(id);
        return view is null ? NotFound() : Ok(view);
    }

    [HttpPost("{id:guid}/acknowledge")]
    public ActionResult<IncidentView> Acknowledge(Guid id, AcknowledgeBody body)
        => _incidents.Acknowledge(id, body.Responder) is { } v ? Ok(v) : NotFound();

    [HttpPost("{id:guid}/escalate")]
    public ActionResult<IncidentView> Escalate(Guid id, EscalateBody body)
        => _incidents.Escalate(id, body.To) is { } v ? Ok(v) : NotFound();

    [HttpPost("{id:guid}/resolve")]
    public ActionResult<IncidentView> Resolve(Guid id, ResolveBody body)
        => _incidents.Resolve(id, body.Resolution) is { } v ? Ok(v) : NotFound();

    [HttpGet("{id:guid}/postmortem")]
    public ActionResult<PostMortem> PostMortem(Guid id)
        => _incidents.GeneratePostMortem(id) is { } pm ? Ok(pm) : NotFound();

    // Seed a failing trace, then open an incident linked to it so automated RCA populates.
    [HttpPost("demo")]
    public async Task<ActionResult<IncidentView>> Demo(CancellationToken ct)
    {
        var root = _tracing.RecordSpan("Chat Request", null, durationMs: 6800, SpanStatus.Error);
        _tracing.RecordRetrieval(root.SpanId, "incident playbook", docCount: 2, topScore: 0.4, durationMs: 95);
        _tracing.RecordMcpToolCall(root.SpanId, "open_incident", "incident", "{\"sev\":1}",
            SpanStatus.Error, durationMs: 5200);

        var view = await _incidents.CreateIncidentAsync(new IncidentRequest
        {
            Title = "MCP tool timeout cascading failure",
            Description = "open_incident tool timed out and failed the request.",
            TraceId = root.TraceId,
            ErrorSpanCount = 2,
            MetricDeviation = 2.4,
        }, ct);
        return Ok(view);
    }
}

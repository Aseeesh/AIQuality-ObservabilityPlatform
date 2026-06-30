using System.Collections.Concurrent;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services;

// =============================================================================
// Incident Management Service
// =============================================================================
//
// Workflow: detect -> classify severity -> assign responders -> create record -> automated RCA
//           -> notify (PagerDuty/OpsGenie/Slack/Email by severity) -> acknowledge -> escalate
//           -> resolve -> post-mortem.
//
// Automated RCA is real cross-service integration: when the incident carries a TraceId, the
// service runs the distributed-tracing analyzer (IDistributedTracingService.AnalyzeTrace) and
// attaches the originating failure, findings, and recommendations. Notifications fan out across
// the registered INotificationChannel implementations. State is in-memory (singleton).
// =============================================================================
public class IncidentService : IIncidentService
{
    private readonly IDistributedTracingService _tracing;
    private readonly IReadOnlyList<INotificationChannel> _channels;
    private readonly ConcurrentDictionary<Guid, IncidentView> _incidents = new();

    // Round-robin responder pools per severity tier.
    private static readonly string[] PrimaryOnCall = { "alex", "sam", "priya" };
    private static readonly string[] SecondaryOnCall = { "jordan", "mei" };
    private int _rotation;

    public IncidentService(IDistributedTracingService tracing, IEnumerable<INotificationChannel> channels)
    {
        _tracing = tracing;
        _channels = channels.ToList();
    }

    // -------------------------------------------------------------------------
    // Create
    // -------------------------------------------------------------------------
    public Task<IncidentView> CreateIncidentAsync(IncidentRequest request, CancellationToken ct = default)
    {
        var severity = request.Severity ?? ClassifySeverity(request);
        var incident = new Incident
        {
            Title = request.Title,
            Description = request.Description,
            Severity = severity,
            Status = IncidentStatus.Open,
            TraceId = request.TraceId,
            Assignee = AssignResponder(severity),
        };
        var view = new IncidentView { Incident = incident };
        AddTimeline(view, $"Opened {severity} '{incident.Title}', assigned to {incident.Assignee}.");

        // Automated RCA from the linked trace.
        if (!string.IsNullOrEmpty(request.TraceId))
        {
            view.Rca = RunAutomatedRca(request.TraceId);
            if (view.Rca?.RootCause is { } rc)
                AddTimeline(view, $"Automated RCA: {rc} ({view.Rca.Confidence:P0} confidence).");
        }

        // Fan out notifications by severity.
        Notify(view, $"[{severity}] {incident.Title}");

        _incidents[incident.Id] = view;
        return Task.FromResult(view);
    }

    // Severity from blast radius (mirrors the Python IncidentManager classification).
    private static IncidentSeverity ClassifySeverity(IncidentRequest r)
    {
        if (r.CriticalLogCount > 0 || r.ErrorSpanCount >= 3 || r.MetricDeviation >= 1.0) return IncidentSeverity.Sev1;
        if (r.ErrorSpanCount >= 1 || r.MetricDeviation >= 0.5) return IncidentSeverity.Sev2;
        if (r.MetricDeviation >= 0.25) return IncidentSeverity.Sev3;
        return IncidentSeverity.Sev4;
    }

    private string AssignResponder(IncidentSeverity severity)
    {
        var pool = severity <= IncidentSeverity.Sev2 ? PrimaryOnCall : SecondaryOnCall;
        return pool[Interlocked.Increment(ref _rotation) % pool.Length];
    }

    private RcaSummary RunAutomatedRca(string traceId)
    {
        var analysis = _tracing.AnalyzeTrace(traceId);
        var summary = new RcaSummary
        {
            PrimarySpanId = analysis.PrimaryRootCauseSpanId,
            Findings = analysis.Findings.Select(f => $"[{f.Category}] {f.Description}").ToList(),
            Recommendations = analysis.Findings.Select(f => f.Recommendation).Distinct().ToList(),
        };
        var primary = analysis.Findings.FirstOrDefault(f => f.Category == "failure")
                      ?? analysis.Findings.FirstOrDefault();
        summary.RootCause = primary?.Description ?? (analysis.Findings.Count == 0 ? "Inconclusive — insufficient trace evidence." : null);
        summary.Confidence = analysis.Findings.Count == 0 ? 0.0
            : analysis.Findings.Any(f => f.Severity == "critical") ? 0.9 : 0.6;
        return summary;
    }

    // -------------------------------------------------------------------------
    // Lifecycle transitions
    // -------------------------------------------------------------------------
    public IncidentView? Acknowledge(Guid id, string responder)
    {
        if (!_incidents.TryGetValue(id, out var view)) return null;
        view.Incident.Status = IncidentStatus.Acknowledged;
        view.Incident.Assignee = responder;
        AddTimeline(view, $"Acknowledged by {responder}.");
        return view;
    }

    public IncidentView? Escalate(Guid id, string to)
    {
        if (!_incidents.TryGetValue(id, out var view)) return null;
        var inc = view.Incident;
        // Bump severity one tier toward Sev1 (numerically lower).
        if (inc.Severity > IncidentSeverity.Sev1) inc.Severity = inc.Severity - 1;
        inc.Status = IncidentStatus.Escalated;
        AddTimeline(view, $"Escalated to {to} (now {inc.Severity}).");
        Notify(view, $"ESCALATED [{inc.Severity}] {inc.Title} -> {to}");
        return view;
    }

    public IncidentView? Resolve(Guid id, string resolution)
    {
        if (!_incidents.TryGetValue(id, out var view)) return null;
        var inc = view.Incident;
        inc.Status = IncidentStatus.Resolved;
        inc.ResolvedAt = DateTimeOffset.UtcNow;
        inc.Resolution = resolution;
        AddTimeline(view, $"Resolved: {resolution}.");
        return view;
    }

    // -------------------------------------------------------------------------
    // Post-mortem
    // -------------------------------------------------------------------------
    public PostMortem? GeneratePostMortem(Guid id)
    {
        if (!_incidents.TryGetValue(id, out var view)) return null;
        var inc = view.Incident;
        var actionItems = view.Rca?.Recommendations.ToList() ?? new List<string>();
        if (actionItems.Count == 0)
            actionItems.Add("Add telemetry/alerting to catch this failure mode earlier.");
        return new PostMortem
        {
            IncidentId = inc.Id,
            Title = inc.Title,
            Severity = inc.Severity,
            RootCause = view.Rca?.RootCause ?? "Root cause not determined.",
            Timeline = view.Timeline,
            ActionItems = actionItems,
            FollowUps = new()
            {
                "Add a regression test / monitor for this failure mode.",
                "Verify alerting fired promptly and routed to the right responder.",
            },
        };
    }

    // -------------------------------------------------------------------------
    // Query
    // -------------------------------------------------------------------------
    public IReadOnlyList<Incident> Active() =>
        _incidents.Values.Select(v => v.Incident)
            .Where(i => i.Status != IncidentStatus.Resolved)
            .OrderBy(i => i.Severity).ThenByDescending(i => i.OpenedAt)
            .ToList();

    public IncidentView? Get(Guid id) => _incidents.TryGetValue(id, out var v) ? v : null;

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------
    private void Notify(IncidentView view, string message)
    {
        foreach (var channel in _channels.Where(c => c.Handles(view.Incident.Severity)))
        {
            var n = channel.Send(view.Incident, message);
            view.Notifications.Add(n);
            AddTimeline(view, $"Notified {n.Channel} ({n.Target}).");
        }
    }

    private static void AddTimeline(IncidentView view, string evt) =>
        view.Timeline.Add(new TimelineEntry { Event = evt });
}

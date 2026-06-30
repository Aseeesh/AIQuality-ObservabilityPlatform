using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using AIQuality.API.Services;
using AIQuality.API.Services.Notifications;
using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;
using Xunit;

namespace AIQuality.Tests.UnitTests;

public class IncidentServiceTests
{
    private static (IncidentService svc, TracingService tracing) NewService()
    {
        var tracing = new TracingService();
        var channels = new INotificationChannel[]
        {
            new PagerDutyChannel(), new OpsGenieChannel(), new SlackChannel(), new EmailChannel(),
        };
        return (new IncidentService(tracing, channels), tracing);
    }

    [Fact]
    public async Task Classifies_severity_from_signals()
    {
        var (svc, _) = NewService();
        var sev1 = await svc.CreateIncidentAsync(new IncidentRequest { Title = "big", MetricDeviation = 1.5 });
        var sev3 = await svc.CreateIncidentAsync(new IncidentRequest { Title = "small", MetricDeviation = 0.3 });
        Assert.Equal(IncidentSeverity.Sev1, sev1.Incident.Severity);
        Assert.Equal(IncidentSeverity.Sev3, sev3.Incident.Severity);
    }

    [Fact]
    public async Task Sev1_pages_pagerduty_and_assigns_responder()
    {
        var (svc, _) = NewService();
        var view = await svc.CreateIncidentAsync(new IncidentRequest { Title = "outage", Severity = IncidentSeverity.Sev1 });
        Assert.Contains(view.Notifications, n => n.Channel == "pagerduty");
        Assert.Contains(view.Notifications, n => n.Channel == "slack");
        Assert.False(string.IsNullOrEmpty(view.Incident.Assignee));
    }

    [Fact]
    public async Task Sev4_does_not_page()
    {
        var (svc, _) = NewService();
        var view = await svc.CreateIncidentAsync(new IncidentRequest { Title = "minor", Severity = IncidentSeverity.Sev4 });
        Assert.DoesNotContain(view.Notifications, n => n.Channel == "pagerduty");
        Assert.Contains(view.Notifications, n => n.Channel == "slack"); // slack handles all
    }

    [Fact]
    public async Task Automated_rca_runs_from_linked_trace()
    {
        var (svc, tracing) = NewService();
        var root = tracing.RecordSpan("Chat Request", null, 6000, SpanStatus.Error);
        tracing.RecordMcpToolCall(root.SpanId, "open_incident", "incident", "{}", SpanStatus.Error, 5200);

        var view = await svc.CreateIncidentAsync(new IncidentRequest
        {
            Title = "tool timeout", Severity = IncidentSeverity.Sev1, TraceId = root.TraceId, ErrorSpanCount = 2,
        });

        Assert.NotNull(view.Rca);
        Assert.True(view.Rca!.Confidence > 0);
        Assert.Contains("open_incident", view.Rca.RootCause);
        Assert.NotEmpty(view.Rca.Recommendations);
    }

    [Fact]
    public async Task Escalation_bumps_severity_and_resolution_closes()
    {
        var (svc, _) = NewService();
        var view = await svc.CreateIncidentAsync(new IncidentRequest { Title = "x", Severity = IncidentSeverity.Sev3 });
        var id = view.Incident.Id;

        var escalated = svc.Escalate(id, "incident-commander")!;
        Assert.Equal(IncidentSeverity.Sev2, escalated.Incident.Severity);
        Assert.Equal(IncidentStatus.Escalated, escalated.Incident.Status);

        var resolved = svc.Resolve(id, "rolled back deploy")!;
        Assert.Equal(IncidentStatus.Resolved, resolved.Incident.Status);
        Assert.NotNull(resolved.Incident.ResolvedAt);
        Assert.DoesNotContain(svc.Active(), i => i.Id == id);
    }

    [Fact]
    public async Task Postmortem_includes_timeline_and_action_items()
    {
        var (svc, tracing) = NewService();
        var root = tracing.RecordSpan("Chat Request", null, 6000, SpanStatus.Error);
        tracing.RecordMcpToolCall(root.SpanId, "open_incident", "incident", "{}", SpanStatus.Error, 5200);
        var view = await svc.CreateIncidentAsync(new IncidentRequest
        {
            Title = "tool timeout", Severity = IncidentSeverity.Sev1, TraceId = root.TraceId, ErrorSpanCount = 2,
        });
        svc.Resolve(view.Incident.Id, "added retry");

        var pm = svc.GeneratePostMortem(view.Incident.Id)!;
        Assert.Equal(view.Incident.Id, pm.IncidentId);
        Assert.NotEmpty(pm.Timeline);
        Assert.NotEmpty(pm.ActionItems);
        Assert.Contains("open_incident", pm.RootCause);
    }
}

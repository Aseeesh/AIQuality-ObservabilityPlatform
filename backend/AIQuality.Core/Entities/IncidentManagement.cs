using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// Request to open an incident. Severity is optional — when omitted the service classifies it
// from the blast-radius signals (error spans, critical logs, metric deviation).
public class IncidentRequest
{
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public IncidentSeverity? Severity { get; set; }
    public string? TraceId { get; set; }                 // when set, automated RCA runs on this trace
    public Dictionary<string, string> Signals { get; set; } = new();
    public int ErrorSpanCount { get; set; }
    public int CriticalLogCount { get; set; }
    public double MetricDeviation { get; set; }          // |actual-baseline|/baseline
}

// A notification dispatched to an external channel (PagerDuty/OpsGenie/Slack/Email).
public class Notification
{
    public string Channel { get; set; } = string.Empty;
    public string Target { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public DateTimeOffset SentAt { get; set; } = DateTimeOffset.UtcNow;
}

public class TimelineEntry
{
    public DateTimeOffset At { get; set; } = DateTimeOffset.UtcNow;
    public string Event { get; set; } = string.Empty;
}

// Summary of automated root-cause analysis attached to an incident.
public class RcaSummary
{
    public string? RootCause { get; set; }
    public double Confidence { get; set; }
    public string? PrimarySpanId { get; set; }
    public List<string> Findings { get; set; } = new();
    public List<string> Recommendations { get; set; } = new();
}

// The full, non-persisted view of an incident: the record + its notifications, timeline, RCA.
public class IncidentView
{
    public Incident Incident { get; set; } = new();
    public List<Notification> Notifications { get; set; } = new();
    public List<TimelineEntry> Timeline { get; set; } = new();
    public RcaSummary? Rca { get; set; }
}

public class PostMortem
{
    public Guid IncidentId { get; set; }
    public string Title { get; set; } = string.Empty;
    public IncidentSeverity Severity { get; set; }
    public string RootCause { get; set; } = string.Empty;
    public List<TimelineEntry> Timeline { get; set; } = new();
    public List<string> ActionItems { get; set; } = new();
    public List<string> FollowUps { get; set; } = new();
}

using AIQuality.Core.Enums;

namespace AIQuality.Core.Entities;

// An operational incident raised from anomalies, SLO breaches, or failing traces. Scalar-only
// so it maps cleanly to EF/Postgres; notifications/timeline/RCA live on the non-persisted
// IncidentView that wraps it.
public class Incident
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public IncidentSeverity Severity { get; set; } = IncidentSeverity.Sev3;
    public IncidentStatus Status { get; set; } = IncidentStatus.Open;
    public DateTimeOffset OpenedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? ResolvedAt { get; set; }
    public string? TraceId { get; set; }
    public string? Assignee { get; set; }
    public string? Resolution { get; set; }
}

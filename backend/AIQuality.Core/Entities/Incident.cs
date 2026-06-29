namespace AIQuality.Core.Entities;

// An operational incident raised from anomalies or SLO breaches.
public class Incident
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Title { get; set; } = string.Empty;
    public DateTimeOffset OpenedAt { get; set; }
    public bool Resolved { get; set; }
}

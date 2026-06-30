using AIQuality.Core.Entities;
using AIQuality.Core.Enums;

namespace AIQuality.Core.Interfaces;

// An outbound notification channel (PagerDuty, OpsGenie, Slack/Teams, Email). Implementations
// decide which severities they handle and how to format/route the message. Registering several
// and resolving IEnumerable<INotificationChannel> lets the incident service fan out by severity.
public interface INotificationChannel
{
    string Name { get; }
    bool Handles(IncidentSeverity severity);
    Notification Send(Incident incident, string message);
}

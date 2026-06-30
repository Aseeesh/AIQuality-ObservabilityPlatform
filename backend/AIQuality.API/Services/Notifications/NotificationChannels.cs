using AIQuality.Core.Entities;
using AIQuality.Core.Enums;
using AIQuality.Core.Interfaces;

namespace AIQuality.API.Services.Notifications;

// Notification channels. Each records the notification it would send; in production the Send
// body would POST to the provider's API (PagerDuty Events v2, OpsGenie Alert API, Slack/Teams
// webhook, SMTP). They are registered as INotificationChannel and fanned out by severity.
//
// Routing policy (who gets paged for what):
//   PagerDuty / OpsGenie  -> Sev1, Sev2   (wake someone up)
//   Slack                 -> all severities (team awareness)
//   Email                 -> Sev1..Sev3   (record + stakeholders)

public abstract class NotificationChannelBase : INotificationChannel
{
    public abstract string Name { get; }
    public abstract bool Handles(IncidentSeverity severity);
    protected abstract string Target(Incident incident);

    public Notification Send(Incident incident, string message)
    {
        // Production: dispatch to the provider here. We record the intent so it is observable.
        return new Notification { Channel = Name, Target = Target(incident), Message = message };
    }
}

public class PagerDutyChannel : NotificationChannelBase
{
    public override string Name => "pagerduty";
    public override bool Handles(IncidentSeverity severity) => severity <= IncidentSeverity.Sev2;
    protected override string Target(Incident incident) => "on-call-primary";
}

public class OpsGenieChannel : NotificationChannelBase
{
    public override string Name => "opsgenie";
    public override bool Handles(IncidentSeverity severity) => severity <= IncidentSeverity.Sev2;
    protected override string Target(Incident incident) => "sre-schedule";
}

public class SlackChannel : NotificationChannelBase
{
    public override string Name => "slack";
    public override bool Handles(IncidentSeverity severity) => true;
    protected override string Target(Incident incident) =>
        incident.Severity <= IncidentSeverity.Sev2 ? "#incidents" : "#ops";
}

public class EmailChannel : NotificationChannelBase
{
    public override string Name => "email";
    public override bool Handles(IncidentSeverity severity) => severity <= IncidentSeverity.Sev3;
    protected override string Target(Incident incident) => "sre-leads@aiquality.dev";
}

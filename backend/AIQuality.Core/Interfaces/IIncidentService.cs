using AIQuality.Core.Entities;

namespace AIQuality.Core.Interfaces;

// Contract for incident lifecycle management: create (classify + assign + notify + auto-RCA),
// acknowledge, escalate, resolve, and post-mortem generation.
public interface IIncidentService
{
    Task<IncidentView> CreateIncidentAsync(IncidentRequest request, CancellationToken ct = default);

    IncidentView? Acknowledge(Guid id, string responder);
    IncidentView? Escalate(Guid id, string to);
    IncidentView? Resolve(Guid id, string resolution);

    PostMortem? GeneratePostMortem(Guid id);

    IReadOnlyList<Incident> Active();
    IncidentView? Get(Guid id);
}

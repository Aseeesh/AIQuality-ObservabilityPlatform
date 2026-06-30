namespace AIQuality.API.Models;

// Small request DTOs for incident lifecycle endpoints. The richer IncidentRequest /
// IncidentView / PostMortem contracts live in AIQuality.Core.Entities.
public record AcknowledgeBody(string Responder);
public record EscalateBody(string To);
public record ResolveBody(string Resolution);

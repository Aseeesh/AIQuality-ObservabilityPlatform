namespace AIQuality.Core.Enums;

// Lever an improvement opportunity pulls. Maps to who/what would action it.
public enum ImprovementArea
{
    Prompt,          // system/prompt engineering changes
    Model,           // model swap or fine-tuning
    KnowledgeBase,   // retrieval/grounding corpus updates
    Configuration,   // gates, guardrails, routing config
    Cost             // cost-reduction (routing, prompt size, caching)
}

// Rough implementation effort, used in priority scoring.
public enum Effort
{
    Low,
    Medium,
    High
}

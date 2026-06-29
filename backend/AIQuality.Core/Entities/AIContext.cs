namespace AIQuality.Core.Entities;

// AI-specific context attached to a span. A single flat record is used (rather than a
// class-per-span-type) because spans are stored/queried uniformly and serialized to the
// UI as one shape — the UI shows whichever fields are populated for a given span kind.
//
// Field groups map to the AI-specific trace kinds the platform cares about:
//   * LLM call        — Model, Prompt, Response, *Tokens, CostUsd, Temperature
//   * Quality check   — QualityScore, QualityVerdict
//   * Model routing   — RoutingDecision, RoutingReason
//   * Knowledge retrieval — RetrievedDocCount, RetrievalQuery, TopScore
//   * MCP tool call   — ToolName, ToolServer, ToolArgsJson
public class AIContext
{
    // Which AI operation this context describes (e.g. "llm_call", "quality_check",
    // "retrieval", "routing", "mcp_tool_call"). Drives UI rendering.
    public string Kind { get; set; } = string.Empty;

    // ---- LLM call ----
    public string? Model { get; set; }
    public string? Prompt { get; set; }
    public string? Response { get; set; }
    public int? PromptTokens { get; set; }
    public int? CompletionTokens { get; set; }
    public int? TotalTokens => PromptTokens.HasValue || CompletionTokens.HasValue
        ? (PromptTokens ?? 0) + (CompletionTokens ?? 0)
        : null;
    public decimal? CostUsd { get; set; }
    public double? Temperature { get; set; }

    // ---- Quality evaluation ----
    public double? QualityScore { get; set; }      // 0..1
    public string? QualityVerdict { get; set; }    // e.g. "Passed" / "Warning" / "Failed"

    // ---- Model routing decision ----
    public string? RoutingDecision { get; set; }   // chosen model/route
    public string? RoutingReason { get; set; }     // why it was chosen

    // ---- Knowledge retrieval ----
    public int? RetrievedDocCount { get; set; }
    public string? RetrievalQuery { get; set; }
    public double? TopScore { get; set; }

    // ---- MCP tool call ----
    public string? ToolName { get; set; }
    public string? ToolServer { get; set; }
    public string? ToolArgsJson { get; set; }
}

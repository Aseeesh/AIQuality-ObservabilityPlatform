// Shared presentation helpers for the tracing UI: colours keyed off span status and the
// AI "kind" so the waterfall and detail panels stay visually consistent.
import type { SpanStatusCode, TraceSpan } from "../../types/span";

export const statusColor = (s: SpanStatusCode): string =>
  s === 2 ? "#dc2626" : s === 1 ? "#16a34a" : "#9ca3af";

// Colour per AI operation kind; plain spans (no aiContext) get a neutral slate.
export const kindColor = (kind?: string | null): string => {
  switch (kind) {
    case "llm_call": return "#7c3aed";       // violet
    case "quality_check": return "#0891b2";   // cyan
    case "retrieval": return "#2563eb";       // blue
    case "routing": return "#d97706";         // amber
    case "mcp_tool_call": return "#db2777";   // pink
    default: return "#64748b";                // slate
  }
};

export const kindLabel = (kind?: string | null): string => {
  switch (kind) {
    case "llm_call": return "LLM";
    case "quality_check": return "Quality";
    case "retrieval": return "Retrieval";
    case "routing": return "Routing";
    case "mcp_tool_call": return "MCP Tool";
    default: return "Span";
  }
};

export const fmtDuration = (ms: number): string =>
  ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${ms} ms`;

export const fmtCost = (usd?: number | null): string =>
  usd == null ? "—" : `$${usd.toFixed(4)}`;

// Build a depth map (root = 0) from parent links, for waterfall indentation.
export function spanDepths(spans: TraceSpan[]): Map<string, number> {
  const byId = new Map(spans.map((s) => [s.spanId, s]));
  const depth = new Map<string, number>();
  const compute = (s: TraceSpan): number => {
    if (depth.has(s.spanId)) return depth.get(s.spanId)!;
    const parent = s.parentSpanId ? byId.get(s.parentSpanId) : undefined;
    const d = parent ? compute(parent) + 1 : 0;
    depth.set(s.spanId, d);
    return d;
  };
  spans.forEach(compute);
  return depth;
}

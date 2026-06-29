// Mirrors the backend span/analysis DTOs (AIQuality.Core.Entities + Enums).
// SpanStatus is serialized as an int by System.Text.Json.
export type SpanStatusCode = 0 | 1 | 2; // Unset | Ok | Error

export const SPAN_STATUS_LABEL: Record<SpanStatusCode, string> = {
  0: "Unset",
  1: "Ok",
  2: "Error",
};

export interface AIContext {
  kind: string; // "llm_call" | "quality_check" | "retrieval" | "routing" | "mcp_tool_call"
  model?: string | null;
  prompt?: string | null;
  response?: string | null;
  promptTokens?: number | null;
  completionTokens?: number | null;
  totalTokens?: number | null;
  costUsd?: number | null;
  temperature?: number | null;
  qualityScore?: number | null;
  qualityVerdict?: string | null;
  routingDecision?: string | null;
  routingReason?: string | null;
  retrievedDocCount?: number | null;
  retrievalQuery?: string | null;
  topScore?: number | null;
  toolName?: string | null;
  toolServer?: string | null;
  toolArgsJson?: string | null;
}

export interface SpanEvent {
  name: string;
  timestamp: string;
  attributes: Record<string, unknown>;
}

export interface TraceSpan {
  traceId: string;
  spanId: string;
  parentSpanId: string | null;
  operationName: string;
  serviceName: string;
  startTime: string;
  endTime: string | null;
  durationMs: number;
  status: SpanStatusCode;
  statusMessage?: string | null;
  attributes: Record<string, unknown>;
  tags: Record<string, string>;
  events: SpanEvent[];
  aiContext?: AIContext | null;
}

export interface TraceSummary {
  traceId: string;
  rootOperation: string;
  startTime: string;
  durationMs: number;
  spanCount: number;
  status: SpanStatusCode;
  totalCostUsd: number;
  totalTokens: number;
}

export interface OperationProfile {
  operation: string;
  count: number;
  p50Ms: number;
  p95Ms: number;
  p99Ms: number;
  maxMs: number;
  errorRate: number;
}

export interface TraceProfile {
  operations: OperationProfile[];
  slowestTraces: TraceSummary[];
  totalSpans: number;
}

export interface RcaFinding {
  category: string; // "failure" | "bottleneck" | "dependency"
  severity: string; // "info" | "warning" | "critical"
  spanId: string;
  operation: string;
  description: string;
  recommendation: string;
}

export interface TraceRootCauseAnalysis {
  traceId: string;
  status: SpanStatusCode;
  primaryRootCauseSpanId: string | null;
  findings: RcaFinding[];
}

export interface SpanQuery {
  traceId?: string;
  operation?: string;
  minDurationMs?: number;
  status?: SpanStatusCode;
  aiKind?: string;
  limit?: number;
}

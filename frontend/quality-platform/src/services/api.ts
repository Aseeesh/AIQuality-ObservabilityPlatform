// Thin client for the AIQuality .NET API.
import type { StartTraceRequest, Trace } from "../types/trace";
import type {
  SpanQuery,
  TraceProfile,
  TraceRootCauseAnalysis,
  TraceSpan,
  TraceSummary,
} from "../types/span";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:5099";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  listTraces: (): Promise<Trace[]> => fetch(`${BASE}/api/tracing`).then(json<Trace[]>),

  startTrace: (body: StartTraceRequest): Promise<Trace> =>
    fetch(`${BASE}/api/tracing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(json<Trace>),

  completeTrace: (id: string, durationMs: number, qualityScore: number | null): Promise<Trace> =>
    fetch(`${BASE}/api/tracing/${id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ durationMs, qualityScore }),
    }).then(json<Trace>),

  // ---- Span-level distributed tracing ----
  listSpanTraces: (limit = 100): Promise<TraceSummary[]> =>
    fetch(`${BASE}/api/spans/traces?limit=${limit}`).then(json<TraceSummary[]>),

  getTraceSpans: (traceId: string): Promise<TraceSpan[]> =>
    fetch(`${BASE}/api/spans/traces/${traceId}`).then(json<TraceSpan[]>),

  querySpans: (query: SpanQuery): Promise<TraceSpan[]> =>
    fetch(`${BASE}/api/spans/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    }).then(json<TraceSpan[]>),

  getProfile: (): Promise<TraceProfile> => fetch(`${BASE}/api/spans/profile`).then(json<TraceProfile>),

  getRca: (traceId: string): Promise<TraceRootCauseAnalysis> =>
    fetch(`${BASE}/api/spans/traces/${traceId}/rca`).then(json<TraceRootCauseAnalysis>),

  seedDemo: (): Promise<{ seeded: string[] }> =>
    fetch(`${BASE}/api/spans/demo`, { method: "POST" }).then(json<{ seeded: string[] }>),
};

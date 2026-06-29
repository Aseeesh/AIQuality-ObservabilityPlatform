// Thin client for the AIQuality .NET API.
import type { StartTraceRequest, Trace } from "../types/trace";

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
};

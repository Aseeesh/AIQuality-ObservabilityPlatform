// Mirrors the backend AIQuality.Core.Entities.Trace shape.
export type TraceStatus = 0 | 1 | 2 | 3; // Pending | Running | Completed | Failed

export const TRACE_STATUS_LABEL: Record<TraceStatus, string> = {
  0: "Pending",
  1: "Running",
  2: "Completed",
  3: "Failed",
};

export interface Trace {
  id: string;
  name: string;
  model: string;
  status: TraceStatus;
  startedAt: string;
  endedAt: string | null;
  durationMs: number;
  qualityScore: number | null;
}

export interface StartTraceRequest {
  name: string;
  model: string;
}

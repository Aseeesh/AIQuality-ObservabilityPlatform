// Shared dashboard types. Where the .NET API exposes a shape we mirror it (tracing, spans,
// evaluation); the monitoring/SLO/incident/feedback shapes mirror the Python services'
// JSON contracts so the same components work against live services or sample data.

export type Page =
  | "overview"
  | "tracing"
  | "evaluation"
  | "monitoring"
  | "slo"
  | "incidents"
  | "feedback";

export interface SLO {
  name: string;
  objective: number;        // e.g. 0.999
  window: string;           // e.g. "30d"
  sli: number;              // measured indicator 0..1
}

export interface ErrorBudgetStatus {
  slo: string;
  consumed: number;         // 0..1 (>1 = over budget)
  remaining: number;
  burnRate: number;
}

export interface SLIPoint {
  t: string;                // time label
  [slo: string]: number | string;
}

export interface QualityTrendPoint {
  t: string;
  overall: number;
  passRate: number;
}

export interface AIInsight {
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
}

export type IncidentSeverity = "P1" | "P2" | "P3" | "P4";
export type IncidentStatus = "open" | "escalated" | "resolved";

export interface Incident {
  id: string;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  openedAt: string;
}

export interface PostMortem {
  incidentId: string;
  title: string;
  rootCause: string;
  actionItems: string[];
}

export interface RcaFindingView {
  category: string;
  severity: string;
  operation: string;
  description: string;
  recommendation: string;
}

export interface RcaAnalysisView {
  incidentId: string;
  rootCause: string;
  confidence: number;
  findings: RcaFindingView[];
}

export interface FeedbackItem {
  id: string;
  sentiment: "positive" | "neutral" | "negative";
  rating: number | null;
  topics: string[];
  text: string;
}

// A single live metric tick streamed over the WebSocket / live feed.
export interface LiveMetric {
  name: string;
  value: number;
  t: number;                // epoch ms
  isAnomaly?: boolean;
}

export interface AlertNotification {
  id: string;
  severity: IncidentSeverity;
  metric: string;
  message: string;
  t: number;
}

// Sample data for the shapes the demo REST API doesn't serve directly (SLOs, incidents,
// post-mortems, feedback, quality trend). In production these come from the Python services'
// endpoints; the components accept the same shapes, so swapping in live fetches is a one-liner.
import type {
  AIInsight, ErrorBudgetStatus, FeedbackItem, Incident, PostMortem,
  QualityTrendPoint, RcaAnalysisView, SLIPoint, SLO,
} from "../types/dashboard";

export const sampleSLOs: SLO[] = [
  { name: "api-availability", objective: 0.999, window: "30d", sli: 0.9994 },
  { name: "eval-latency", objective: 0.99, window: "7d", sli: 0.972 },
  { name: "quality-score", objective: 0.95, window: "30d", sli: 0.963 },
];

export const sampleErrorBudgets: ErrorBudgetStatus[] = [
  { slo: "api-availability", consumed: 0.4, remaining: 0.6, burnRate: 0.9 },
  { slo: "eval-latency", consumed: 1.2, remaining: 0, burnRate: 6.1 },
  { slo: "quality-score", consumed: 0.74, remaining: 0.26, burnRate: 1.4 },
];

export const sampleSLISeries: SLIPoint[] = Array.from({ length: 12 }, (_, i) => ({
  t: `${i * 2}h`,
  "api-availability": 0.999 + (Math.random() - 0.5) * 0.001,
  "quality-score": 0.96 + (Math.random() - 0.5) * 0.03,
}));

export const sampleQualityTrend: QualityTrendPoint[] = Array.from({ length: 10 }, (_, i) => ({
  t: `run ${i + 1}`,
  overall: 0.78 + i * 0.012 + (Math.random() - 0.5) * 0.03,
  passRate: 0.7 + i * 0.02 + (Math.random() - 0.5) * 0.04,
}));

export const sampleInsights: AIInsight[] = [
  { severity: "critical", title: "eval-latency error budget exhausted", detail: "Burn rate 6.1× — p95 latency regressed after the last deploy." },
  { severity: "warning", title: "Accuracy trending down on rag dataset", detail: "Down 4% over 3 runs; retrieval coverage suspected." },
  { severity: "info", title: "Feedback volume up 22%", detail: "Mostly praise; tone complaints down week-over-week." },
];

export const sampleIncidents: Incident[] = [
  { id: "INC-2f1a", title: "MCP tool timeout cascading failures", severity: "P1", status: "escalated", openedAt: "2026-06-30T08:12:00Z" },
  { id: "INC-9c33", title: "Quality regression on summarization", severity: "P2", status: "open", openedAt: "2026-06-30T07:40:00Z" },
  { id: "INC-71be", title: "Elevated eval latency", severity: "P3", status: "open", openedAt: "2026-06-29T22:05:00Z" },
];

export const samplePostMortems: PostMortem[] = [
  {
    incidentId: "INC-1a02", title: "Retrieval outage degraded grounding",
    rootCause: "Vector store connection pool exhausted under load.",
    actionItems: ["Add connection-pool autoscaling", "Add a grounding SLO + alert"],
  },
];

export const sampleRca: RcaAnalysisView = {
  incidentId: "INC-2f1a",
  rootCause: "'MCP Tool: open_incident' (mcp_tool_call) timed out and propagated up the trace.",
  confidence: 0.9,
  findings: [
    { category: "failure", severity: "critical", operation: "MCP Tool: open_incident", description: "Downstream tool timed out after 5.2s.", recommendation: "Add timeout+retry+circuit-breaker." },
    { category: "dependency", severity: "warning", operation: "Chat Request", description: "Tool failure failed the parent request.", recommendation: "Add a degraded-mode fallback." },
  ],
};

export const sampleFeedback: FeedbackItem[] = [
  { id: "fb-01", sentiment: "negative", rating: 1, topics: ["accuracy"], text: "completely wrong and inaccurate" },
  { id: "fb-02", sentiment: "positive", rating: 5, topics: [], text: "very helpful and clear" },
  { id: "fb-03", sentiment: "negative", rating: 2, topics: ["latency", "completeness"], text: "too slow and vague" },
  { id: "fb-04", sentiment: "neutral", rating: 3, topics: [], text: "it was okay" },
];

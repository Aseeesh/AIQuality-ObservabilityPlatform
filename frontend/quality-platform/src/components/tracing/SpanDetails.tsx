import type { AIContext, TraceSpan } from "../../types/span";
import { fmtCost, fmtDuration, kindColor, kindLabel, statusColor } from "./spanUtils";
import { SPAN_STATUS_LABEL } from "../../types/span";

// Inspector for a single selected span: status/duration header, AI-specific panel
// (LLM tokens+cost, quality score, retrieval, routing, MCP tool), then raw attributes.
export function SpanDetails({ span }: { span: TraceSpan }) {
  const ai = span.aiContext ?? undefined;
  return (
    <div style={{ fontSize: 13 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <span style={{ width: 10, height: 10, borderRadius: 3, background: kindColor(ai?.kind) }} />
        <strong>{span.operationName}</strong>
        <span style={{ marginLeft: "auto", color: statusColor(span.status), fontWeight: 600 }}>
          {SPAN_STATUS_LABEL[span.status]}
        </span>
      </div>

      <Row label="Duration" value={fmtDuration(span.durationMs)} />
      <Row label="Kind" value={kindLabel(ai?.kind)} />
      <Row label="Span ID" value={span.spanId} mono />
      {span.parentSpanId && <Row label="Parent" value={span.parentSpanId} mono />}
      {span.statusMessage && <Row label="Error" value={span.statusMessage} />}

      {ai && <AIPanel ai={ai} />}

      {Object.keys(span.attributes ?? {}).length > 0 && (
        <>
          <h4 style={h4}>Attributes</h4>
          {Object.entries(span.attributes).map(([k, v]) => (
            <Row key={k} label={k} value={String(v)} mono />
          ))}
        </>
      )}
    </div>
  );
}

function AIPanel({ ai }: { ai: AIContext }) {
  switch (ai.kind) {
    case "llm_call":
      return (
        <>
          <h4 style={h4}>LLM Call</h4>
          <Row label="Model" value={ai.model ?? "—"} />
          <div style={{ display: "flex", gap: 8, margin: "6px 0" }}>
            <Stat label="Prompt tok" value={ai.promptTokens ?? 0} />
            <Stat label="Completion tok" value={ai.completionTokens ?? 0} />
            <Stat label="Total tok" value={ai.totalTokens ?? 0} />
            <Stat label="Cost" value={fmtCost(ai.costUsd)} />
          </div>
          {ai.temperature != null && <Row label="Temperature" value={String(ai.temperature)} />}
          {ai.prompt && <Collapsible label="Prompt" text={ai.prompt} />}
          {ai.response && <Collapsible label="Response" text={ai.response} />}
        </>
      );
    case "quality_check":
      return (
        <>
          <h4 style={h4}>Quality Evaluation</h4>
          <QualityBar score={ai.qualityScore ?? 0} verdict={ai.qualityVerdict ?? ""} />
        </>
      );
    case "retrieval":
      return (
        <>
          <h4 style={h4}>Knowledge Retrieval</h4>
          <Row label="Query" value={ai.retrievalQuery ?? "—"} />
          <Row label="Docs" value={String(ai.retrievedDocCount ?? 0)} />
          <Row label="Top score" value={ai.topScore != null ? ai.topScore.toFixed(2) : "—"} />
        </>
      );
    case "routing":
      return (
        <>
          <h4 style={h4}>Model Routing</h4>
          <Row label="Chosen" value={ai.routingDecision ?? "—"} />
          <Row label="Reason" value={ai.routingReason ?? "—"} />
        </>
      );
    case "mcp_tool_call":
      return (
        <>
          <h4 style={h4}>MCP Tool Call</h4>
          <Row label="Tool" value={ai.toolName ?? "—"} />
          <Row label="Server" value={ai.toolServer ?? "—"} />
          {ai.toolArgsJson && <Collapsible label="Args" text={ai.toolArgsJson} />}
        </>
      );
    default:
      return null;
  }
}

function QualityBar({ score, verdict }: { score: number; verdict: string }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? "#16a34a" : score >= 0.6 ? "#d97706" : "#dc2626";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span>{verdict}</span>
        <span>{pct}%</span>
      </div>
      <div style={{ height: 8, background: "#e2e8f0", borderRadius: 4 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
    </div>
  );
}

const h4: React.CSSProperties = { margin: "14px 0 6px", fontSize: 13, color: "#475569" };

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 8, padding: "2px 0" }}>
      <span style={{ color: "#64748b", minWidth: 110 }}>{label}</span>
      <span style={{ fontFamily: mono ? "ui-monospace, monospace" : undefined, wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ flex: 1, background: "#f8fafc", borderRadius: 6, padding: "6px 8px", textAlign: "center" }}>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{value}</div>
      <div style={{ fontSize: 11, color: "#64748b" }}>{label}</div>
    </div>
  );
}

function Collapsible({ label, text }: { label: string; text: string }) {
  return (
    <details style={{ margin: "4px 0" }}>
      <summary style={{ cursor: "pointer", color: "#64748b" }}>{label}</summary>
      <pre style={{ whiteSpace: "pre-wrap", background: "#f8fafc", padding: 8, borderRadius: 6, fontSize: 12 }}>{text}</pre>
    </details>
  );
}

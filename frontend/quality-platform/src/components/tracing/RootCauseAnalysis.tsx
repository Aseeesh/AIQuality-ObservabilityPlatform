import type { RcaFinding, TraceRootCauseAnalysis } from "../../types/span";

// Renders automated root-cause findings for a trace. Findings are grouped visually by
// severity; the originating-failure span id is surfaced so the user can jump to it in the
// waterfall (clicking a finding selects its span).
export function RootCauseAnalysis({
  rca,
  onSelectSpan,
}: {
  rca: TraceRootCauseAnalysis;
  onSelectSpan: (spanId: string) => void;
}) {
  if (rca.findings.length === 0)
    return <p style={{ color: "#16a34a", fontSize: 13 }}>No issues detected — trace looks healthy.</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {rca.findings.map((f, i) => (
        <FindingCard
          key={i}
          f={f}
          primary={f.spanId === rca.primaryRootCauseSpanId}
          onClick={() => onSelectSpan(f.spanId)}
        />
      ))}
    </div>
  );
}

function FindingCard({ f, primary, onClick }: { f: RcaFinding; primary: boolean; onClick: () => void }) {
  const color =
    f.severity === "critical" ? "#dc2626" : f.severity === "warning" ? "#d97706" : "#2563eb";
  return (
    <div
      onClick={onClick}
      style={{
        cursor: "pointer",
        borderLeft: `4px solid ${color}`,
        background: "#f8fafc",
        borderRadius: 6,
        padding: "8px 10px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
        <span style={{ color, fontWeight: 700, textTransform: "uppercase" }}>{f.category}</span>
        <span style={{ color: "#64748b" }}>{f.operation}</span>
        {primary && (
          <span style={{ marginLeft: "auto", background: "#fee2e2", color: "#b91c1c", borderRadius: 10, padding: "1px 8px", fontWeight: 600 }}>
            root cause
          </span>
        )}
      </div>
      <div style={{ fontSize: 13, margin: "4px 0" }}>{f.description}</div>
      <div style={{ fontSize: 12, color: "#475569" }}>→ {f.recommendation}</div>
    </div>
  );
}

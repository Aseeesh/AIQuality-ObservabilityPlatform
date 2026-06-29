import { useEffect, useMemo, useState } from "react";
import { api } from "../../services/api";
import type { SpanStatusCode, TraceSummary } from "../../types/span";
import { SPAN_STATUS_LABEL } from "../../types/span";
import { fmtCost, fmtDuration, statusColor } from "./spanUtils";

// Trace explorer: a filterable, searchable list of recent traces. Filtering is done
// client-side over the loaded summaries (search by trace id / root operation, status, and a
// minimum-duration slider) which keeps the interaction instant; the backend also supports
// server-side span queries for larger datasets via api.querySpans.
export function TraceExplorer({
  selectedTraceId,
  onSelect,
}: {
  selectedTraceId?: string;
  onSelect: (traceId: string) => void;
}) {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<SpanStatusCode | "all">("all");
  const [minDuration, setMinDuration] = useState(0);

  async function refresh() {
    try {
      setTraces(await api.listSpanTraces());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(
    () =>
      traces.filter(
        (t) =>
          (status === "all" || t.status === status) &&
          t.durationMs >= minDuration &&
          (search === "" ||
            t.traceId.includes(search) ||
            t.rootOperation.toLowerCase().includes(search.toLowerCase()))
      ),
    [traces, search, status, minDuration]
  );

  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
        <input
          placeholder="Search trace id or operation…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: "1 1 220px", padding: "4px 8px" }}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value === "all" ? "all" : (Number(e.target.value) as SpanStatusCode))}>
          <option value="all">All statuses</option>
          <option value={1}>Ok</option>
          <option value={2}>Error</option>
        </select>
        <label style={{ fontSize: 12, color: "#475569" }}>
          min {fmtDuration(minDuration)}
          <input type="range" min={0} max={8000} step={100} value={minDuration} onChange={(e) => setMinDuration(Number(e.target.value))} style={{ verticalAlign: "middle", marginLeft: 6 }} />
        </label>
        <button onClick={refresh}>Refresh</button>
      </div>

      {error && <p style={{ color: "crimson" }}>API error: {error}</p>}

      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        <thead>
          <tr>
            {["", "Trace", "Root operation", "Duration", "Spans", "Cost", "Tokens"].map((h, i) => (
              <th key={i} style={th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((t) => (
            <tr
              key={t.traceId}
              onClick={() => onSelect(t.traceId)}
              style={{ cursor: "pointer", background: t.traceId === selectedTraceId ? "#eef2ff" : "transparent" }}
            >
              <td style={td}><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 4, background: statusColor(t.status) }} /></td>
              <td style={{ ...td, fontFamily: "ui-monospace, monospace" }}>{t.traceId.slice(0, 12)}</td>
              <td style={td}>{t.rootOperation}</td>
              <td style={td}>{fmtDuration(t.durationMs)}</td>
              <td style={td}>{t.spanCount}</td>
              <td style={td}>{fmtCost(t.totalCostUsd)}</td>
              <td style={td}>{t.totalTokens}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td style={td} colSpan={7}>No traces match. Seed demo data or adjust filters.</td></tr>
          )}
        </tbody>
      </table>
      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>
        Showing {filtered.length} of {traces.length} traces · {SPAN_STATUS_LABEL[2]} traces are flagged red.
      </div>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid #e2e8f0", padding: "6px 8px" };
const td: React.CSSProperties = { borderBottom: "1px solid #f1f5f9", padding: "6px 8px" };

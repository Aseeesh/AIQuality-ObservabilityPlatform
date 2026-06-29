import { useEffect, useState } from "react";
import { api } from "../../services/api";
import type { TraceProfile } from "../../types/span";
import { fmtCost, fmtDuration, statusColor } from "./spanUtils";

// Performance profiling view: per-operation latency percentiles (p50/p95/p99) rendered as a
// horizontal distribution bar, plus the slowest traces for quick drill-in. Operations are
// sorted by p95 (the backend already does this) so the worst tail latency floats to the top.
export function PerformanceProfiling({ onSelectTrace }: { onSelectTrace: (traceId: string) => void }) {
  const [profile, setProfile] = useState<TraceProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getProfile().then(setProfile).catch((e) => setError((e as Error).message));
  }, []);

  if (error) return <p style={{ color: "crimson" }}>Failed to load profile: {error}</p>;
  if (!profile) return <p>Loading profile…</p>;

  const max = Math.max(1, ...profile.operations.map((o) => o.maxMs));

  return (
    <div>
      <h3 style={hdr}>Operation latency ({profile.totalSpans} spans)</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {profile.operations.map((o) => (
          <div key={o.operation}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <span>{o.operation} <span style={{ color: "#94a3b8" }}>×{o.count}</span></span>
              <span style={{ color: "#475569" }}>
                p50 {fmtDuration(o.p50Ms)} · p95 {fmtDuration(o.p95Ms)} · p99 {fmtDuration(o.p99Ms)}
                {o.errorRate > 0 && <span style={{ color: "#dc2626" }}> · {Math.round(o.errorRate * 100)}% err</span>}
              </span>
            </div>
            {/* Distribution bar: p50 fill, p95 marker, p99 marker, on a shared axis. */}
            <div style={{ position: "relative", height: 14, background: "#f1f5f9", borderRadius: 7, marginTop: 3 }}>
              <div style={{ position: "absolute", left: 0, width: `${(o.p50Ms / max) * 100}%`, height: "100%", background: "#93c5fd", borderRadius: 7 }} />
              <Marker pos={(o.p95Ms / max) * 100} color="#2563eb" />
              <Marker pos={(o.p99Ms / max) * 100} color="#1e3a8a" />
            </div>
          </div>
        ))}
      </div>

      <h3 style={{ ...hdr, marginTop: 20 }}>Slowest traces</h3>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        <thead>
          <tr>{["", "Trace", "Root", "Duration", "Spans", "Cost"].map((h, i) => <th key={i} style={th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {profile.slowestTraces.map((t) => (
            <tr key={t.traceId} onClick={() => onSelectTrace(t.traceId)} style={{ cursor: "pointer" }}>
              <td style={td}><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 4, background: statusColor(t.status) }} /></td>
              <td style={{ ...td, fontFamily: "ui-monospace, monospace" }}>{t.traceId.slice(0, 12)}</td>
              <td style={td}>{t.rootOperation}</td>
              <td style={td}>{fmtDuration(t.durationMs)}</td>
              <td style={td}>{t.spanCount}</td>
              <td style={td}>{fmtCost(t.totalCostUsd)}</td>
            </tr>
          ))}
          {profile.slowestTraces.length === 0 && <tr><td style={td} colSpan={6}>No traces yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

function Marker({ pos, color }: { pos: number; color: string }) {
  return <div style={{ position: "absolute", left: `${Math.min(pos, 99)}%`, top: -2, width: 2, height: 18, background: color }} />;
}

const hdr: React.CSSProperties = { fontSize: 14, margin: "0 0 8px" };
const th: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid #e2e8f0", padding: "6px 8px" };
const td: React.CSSProperties = { borderBottom: "1px solid #f1f5f9", padding: "6px 8px" };

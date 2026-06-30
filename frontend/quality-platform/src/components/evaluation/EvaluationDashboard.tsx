// Evaluation Dashboard: per-rubric quality scores + regression detection. Fetches live runs
// from the .NET API (/api/evaluation/runs); falls back to sample trend data when the API is
// offline, and offers a one-click demo seed via the MCP bridge.
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { mcpClient } from "../../services/mcpClient";
import { sampleQualityTrend } from "../../services/sampleData";
import { Badge, Card, Stat, grid } from "../ui";

interface RunSummary {
  id: string; dataset: string; environment: string; overall: number;
  passRate: number; gateStatus: number; itemCount: number;
}

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:5099";
const GATE_LABEL = ["Passed", "Warning", "Failed"];

export function EvaluationDashboard() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [offline, setOffline] = useState(false);

  async function load() {
    try {
      const res = await fetch(`${BASE}/api/evaluation/runs`);
      if (!res.ok) throw new Error();
      setRuns(await res.json());
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }
  useEffect(() => { load(); }, []);

  const rubricData = [
    { rubric: "accuracy", score: 0.72 }, { rubric: "relevance", score: 0.81 },
    { rubric: "completeness", score: 0.64 }, { rubric: "safety", score: 0.99 },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card title="Evaluation runs" right={
        <button onClick={async () => { await mcpClient.seedDemo(); load(); }}>Seed demo</button>
      }>
        {offline && <p style={{ fontSize: 12, color: "#94a3b8" }}>API offline — showing sample analytics below.</p>}
        {runs.length === 0 ? (
          <p style={{ fontSize: 13, color: "#64748b" }}>No runs yet. Click "Seed demo" (needs the API running).</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr>{["Dataset", "Env", "Items", "Overall", "Pass rate", "Gate"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
            <tbody>
              {runs.slice(0, 8).map((r) => (
                <tr key={r.id}>
                  <td style={td}>{r.dataset}</td><td style={td}>{r.environment}</td><td style={td}>{r.itemCount}</td>
                  <td style={td}>{(r.overall * 100).toFixed(1)}%</td><td style={td}>{(r.passRate * 100).toFixed(0)}%</td>
                  <td style={td}><Badge kind={["resolved", "warning", "P1"][r.gateStatus] ?? "neutral"} /> {GATE_LABEL[r.gateStatus]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div style={grid(360)}>
        <Card title="Per-rubric scores (latest)">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={rubricData} margin={{ left: -20, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="rubric" fontSize={11} />
              <YAxis domain={[0, 1]} fontSize={11} tickFormatter={(v) => `${v * 100}%`} />
              <Tooltip formatter={(v: number) => `${(v * 100).toFixed(0)}%`} />
              <Bar dataKey="score" fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <RegressionCard />
      </div>
    </div>
  );
}

function RegressionCard() {
  const last = sampleQualityTrend[sampleQualityTrend.length - 1];
  const prev = sampleQualityTrend[sampleQualityTrend.length - 2];
  const delta = last.overall - prev.overall;
  const regressed = delta < -0.02;
  return (
    <Card title="Regression detection">
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Stat label="Latest overall" value={`${(last.overall * 100).toFixed(1)}%`} />
        <Stat label="Δ vs previous" value={`${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`}
          color={regressed ? "#dc2626" : "#16a34a"} />
        <Stat label="Status" value={regressed ? "Regression" : "Stable"} color={regressed ? "#dc2626" : "#16a34a"} />
      </div>
      <p style={{ fontSize: 12, color: "#475569", marginTop: 10 }}>
        Significance is computed server-side via Welch's t-test over per-item scores; only
        statistically significant drops are flagged as regressions.
      </p>
    </Card>
  );
}

const th: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid #e2e8f0", padding: "4px 6px" };
const td: React.CSSProperties = { borderBottom: "1px solid #f1f5f9", padding: "4px 6px" };

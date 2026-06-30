// SLO Dashboard: SLO list with compliance, SLI trend chart, and error-budget status.
// Mirrors the prompt's <SLODashboard><SLOList/><SLIChart/><ErrorBudget/></SLODashboard>.
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ErrorBudgetStatus, SLIPoint, SLO } from "../../types/dashboard";
import { sampleErrorBudgets, sampleSLISeries, sampleSLOs } from "../../services/sampleData";
import { Card, grid } from "../ui";

export function SLODashboard() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={grid(280)}>
        <SLOList slos={sampleSLOs} />
        <ErrorBudget status={sampleErrorBudgets} />
      </div>
      <SLIChart metrics={sampleSLISeries} />
    </div>
  );
}

function SLOList({ slos }: { slos: SLO[] }) {
  return (
    <Card title="SLOs">
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr>{["SLO", "Window", "SLI", "Objective", ""].map((h) => <th key={h} style={th}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {slos.map((s) => {
            const met = s.sli >= s.objective;
            return (
              <tr key={s.name}>
                <td style={td}>{s.name}</td>
                <td style={td}>{s.window}</td>
                <td style={td}>{(s.sli * 100).toFixed(2)}%</td>
                <td style={td}>{(s.objective * 100).toFixed(1)}%</td>
                <td style={{ ...td, color: met ? "#16a34a" : "#dc2626", fontWeight: 600 }}>
                  {met ? "met" : "breached"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function ErrorBudget({ status }: { status: ErrorBudgetStatus[] }) {
  return (
    <Card title="Error budgets">
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {status.map((b) => {
          const over = b.consumed >= 1;
          const pct = Math.min(100, b.consumed * 100);
          return (
            <div key={b.slo}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span>{b.slo}</span>
                <span style={{ color: over ? "#dc2626" : "#475569" }}>
                  {over ? "exhausted" : `${(b.remaining * 100).toFixed(0)}% left`} · burn {b.burnRate.toFixed(1)}×
                </span>
              </div>
              <div style={{ height: 8, background: "#e2e8f0", borderRadius: 4, marginTop: 4 }}>
                <div style={{ width: `${pct}%`, height: "100%", borderRadius: 4,
                  background: over ? "#dc2626" : b.burnRate > 2 ? "#d97706" : "#16a34a" }} />
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function SLIChart({ metrics }: { metrics: SLIPoint[] }) {
  return (
    <Card title="SLI trend (quality-score vs availability)">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={metrics} margin={{ left: -20, right: 8, top: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="t" fontSize={11} />
          <YAxis domain={[0.9, 1]} fontSize={11} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
          <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
          <Area type="monotone" dataKey="quality-score" stroke="#7c3aed" fill="#7c3aed22" />
          <Area type="monotone" dataKey="api-availability" stroke="#2563eb" fill="#2563eb22" />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
}

const th: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid #e2e8f0", padding: "4px 6px" };
const td: React.CSSProperties = { borderBottom: "1px solid #f1f5f9", padding: "4px 6px" };

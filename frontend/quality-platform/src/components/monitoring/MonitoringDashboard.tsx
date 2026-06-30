// Monitoring page: live, WebSocket-fed metric charts with anomaly highlighting, plus the
// rolling alert feed. Reads the real-time buffers from the Zustand store (populated by
// useLiveFeed) so the charts update every tick.
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from "recharts";
import { useDashboardStore } from "../../store/useDashboardStore";
import type { LiveMetric } from "../../types/dashboard";
import { Badge, Card, Stat, grid } from "../ui";

const COLORS: Record<string, string> = { "quality-score": "#7c3aed", "latency-ms": "#2563eb", "error-rate": "#dc2626" };

export function MonitoringDashboard() {
  const liveMetrics = useDashboardStore((s) => s.liveMetrics);
  const connected = useDashboardStore((s) => s.connected);
  const names = Object.keys(liveMetrics);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card title="Live monitoring" right={<Badge kind={connected ? "resolved" : "open"} />}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {names.map((n) => {
            const series = liveMetrics[n];
            const last = series[series.length - 1];
            const anomalies = series.filter((m) => m.isAnomaly).length;
            return <Stat key={n} label={`${n}${anomalies ? ` · ${anomalies} anomalies` : ""}`}
              value={last ? last.value : "—"} color={last?.isAnomaly ? "#dc2626" : COLORS[n]} />;
          })}
          {names.length === 0 && <span style={{ color: "#64748b", fontSize: 13 }}>Waiting for live data…</span>}
        </div>
      </Card>

      <div style={grid(360)}>
        {names.map((n) => <MetricChart key={n} name={n} series={liveMetrics[n]} />)}
      </div>

      <AlertFeed />
    </div>
  );
}

function MetricChart({ name, series }: { name: string; series: LiveMetric[] }) {
  const data = series.map((m) => ({ t: new Date(m.t).toLocaleTimeString(), value: m.value, isAnomaly: m.isAnomaly }));
  const anomalyPoints = data.filter((d) => d.isAnomaly);
  return (
    <Card title={name}>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="t" fontSize={10} minTickGap={40} />
          <YAxis fontSize={10} />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke={COLORS[name] ?? "#334155"} strokeWidth={2} dot={false} isAnimationActive={false} />
          {/* Overlay anomalies as red dots. */}
          <Scatter data={anomalyPoints} dataKey="value" fill="#dc2626" />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

function AlertFeed() {
  const alerts = useDashboardStore((s) => s.alerts);
  const dismiss = useDashboardStore((s) => s.dismissAlert);
  return (
    <Card title={`Alerts (${alerts.length})`}>
      {alerts.length === 0 && <p style={{ fontSize: 13, color: "#64748b" }}>No active alerts.</p>}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {alerts.map((a) => (
          <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13,
            background: "#fef2f2", borderRadius: 6, padding: "4px 8px" }}>
            <Badge kind={a.severity} />
            <span>{a.message}</span>
            <span style={{ marginLeft: "auto", color: "#94a3b8", fontSize: 11 }}>
              {new Date(a.t).toLocaleTimeString()}
            </span>
            <button onClick={() => dismiss(a.id)} style={{ border: "none", background: "transparent", cursor: "pointer" }}>✕</button>
          </div>
        ))}
      </div>
    </Card>
  );
}

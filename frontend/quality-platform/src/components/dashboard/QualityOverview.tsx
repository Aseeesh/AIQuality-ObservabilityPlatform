// Quality Overview page: headline quality score + SLO/incident status, a quality trend chart,
// and AI-generated insights. Mirrors <QualityOverview><QualityScore/><TrendChart/><AIInsights/>.
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AIInsight, QualityTrendPoint } from "../../types/dashboard";
import { sampleInsights, sampleQualityTrend, sampleIncidents, sampleSLOs } from "../../services/sampleData";
import { Badge, Card, Stat, grid } from "../ui";

export function QualityOverview() {
  const overall = sampleQualityTrend[sampleQualityTrend.length - 1].overall;
  const slosMet = sampleSLOs.filter((s) => s.sli >= s.objective).length;
  const openIncidents = sampleIncidents.filter((i) => i.status !== "resolved").length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card title="At a glance">
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <QualityScore score={overall} />
          <Stat label="SLOs met" value={`${slosMet}/${sampleSLOs.length}`}
            color={slosMet === sampleSLOs.length ? "#16a34a" : "#d97706"} />
          <Stat label="Open incidents" value={openIncidents} color={openIncidents ? "#dc2626" : "#16a34a"} />
          <Stat label="P1 active" value={sampleIncidents.filter((i) => i.severity === "P1" && i.status !== "resolved").length} color="#dc2626" />
        </div>
      </Card>

      <div style={grid(360)}>
        <TrendChart trends={sampleQualityTrend} />
        <AIInsights insights={sampleInsights} />
      </div>
    </div>
  );
}

function QualityScore({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.85 ? "#16a34a" : score >= 0.7 ? "#d97706" : "#dc2626";
  return (
    <div style={{ background: "#f8fafc", borderRadius: 8, padding: "10px 18px", textAlign: "center" }}>
      <div style={{ fontSize: 34, fontWeight: 800, color }}>{pct}</div>
      <div style={{ fontSize: 12, color: "#64748b" }}>Quality score</div>
    </div>
  );
}

function TrendChart({ trends }: { trends: QualityTrendPoint[] }) {
  return (
    <Card title="Quality trend">
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={trends} margin={{ left: -20, right: 8, top: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
          <XAxis dataKey="t" fontSize={11} />
          <YAxis domain={[0.6, 1]} fontSize={11} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
          <Tooltip formatter={(v: number) => `${(v * 100).toFixed(1)}%`} />
          <Line type="monotone" dataKey="overall" stroke="#7c3aed" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="passRate" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

function AIInsights({ insights }: { insights: AIInsight[] }) {
  return (
    <Card title="AI insights">
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {insights.map((i, idx) => (
          <div key={idx} style={{ borderLeft: "3px solid #cbd5e1", paddingLeft: 10 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Badge kind={i.severity} />
              <strong style={{ fontSize: 13 }}>{i.title}</strong>
            </div>
            <div style={{ fontSize: 12, color: "#475569", marginTop: 2 }}>{i.detail}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

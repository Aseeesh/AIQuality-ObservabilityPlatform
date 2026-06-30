// Feedback Hub: user feedback stream, sentiment distribution, and improvement suggestions
// mined from negative-topic feedback (the same levers the feedback-processor produces).
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { sampleFeedback } from "../../services/sampleData";
import { Badge, Card, grid } from "../ui";

const SENTIMENT_COLOR: Record<string, string> = { positive: "#16a34a", neutral: "#64748b", negative: "#dc2626" };

const TOPIC_LEVER: Record<string, string> = {
  accuracy: "Tighten grounding / raise the accuracy gate.",
  latency: "Optimise the slow path or route to a faster model.",
  completeness: "Prompt for fuller answers; raise the completeness gate.",
  tone: "Adjust system-prompt tone; add a tone rubric.",
};

export function FeedbackHub() {
  const counts = sampleFeedback.reduce<Record<string, number>>((acc, f) => {
    acc[f.sentiment] = (acc[f.sentiment] ?? 0) + 1;
    return acc;
  }, {});
  const pieData = Object.entries(counts).map(([name, value]) => ({ name, value }));

  const negativeTopics = [...new Set(sampleFeedback.filter((f) => f.sentiment === "negative").flatMap((f) => f.topics))];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={grid(300)}>
        <Card title="Sentiment">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} label>
                {pieData.map((d) => <Cell key={d.name} fill={SENTIMENT_COLOR[d.name]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Improvement suggestions">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {negativeTopics.length === 0 && <p style={{ fontSize: 13, color: "#64748b" }}>No negative themes.</p>}
            {negativeTopics.map((t) => (
              <div key={t} style={{ fontSize: 13 }}>
                <Badge kind="warning" /> <strong>{t}</strong>
                <div style={{ color: "#475569" }}>{TOPIC_LEVER[t] ?? "Investigate this feedback theme."}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title={`User feedback (${sampleFeedback.length})`}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {sampleFeedback.map((f) => (
            <div key={f.id} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
              <Badge kind={f.sentiment} />
              <span style={{ color: "#64748b" }}>{f.rating != null ? `★${f.rating}` : "—"}</span>
              <span>{f.text}</span>
              {f.topics.length > 0 && <span style={{ marginLeft: "auto", color: "#94a3b8" }}>{f.topics.join(", ")}</span>}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

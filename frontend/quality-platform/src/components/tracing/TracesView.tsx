import { useEffect, useState } from "react";
import { api } from "../../services/api";
import { TRACE_STATUS_LABEL, type Trace } from "../../types/trace";

// Live table of recent traces with a quick "start trace" action.
export function TracesView() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("chat-completion");
  const [model, setModel] = useState("claude-opus-4-8");

  async function refresh() {
    try {
      setTraces(await api.listTraces());
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  async function start() {
    try {
      const trace = await api.startTrace({ name, model });
      // Simulate completion so the demo shows a full lifecycle.
      await api.completeTrace(trace.id, Math.round(200 + Math.random() * 1500), Math.random());
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <section>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" />
        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="model" />
        <button onClick={start}>Start trace</button>
        <button onClick={refresh}>Refresh</button>
      </div>

      {error && <p style={{ color: "crimson" }}>API error: {error}</p>}

      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {["Name", "Model", "Status", "Duration", "Quality"].map((h) => (
              <th key={h} style={th}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {traces.map((t) => (
            <tr key={t.id}>
              <td style={td}>{t.name}</td>
              <td style={td}>{t.model}</td>
              <td style={td}>{TRACE_STATUS_LABEL[t.status]}</td>
              <td style={td}>{t.durationMs} ms</td>
              <td style={td}>{t.qualityScore == null ? "—" : t.qualityScore.toFixed(2)}</td>
            </tr>
          ))}
          {traces.length === 0 && (
            <tr><td style={td} colSpan={5}>No traces yet.</td></tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

const th: React.CSSProperties = { textAlign: "left", borderBottom: "2px solid #ccc", padding: "6px 8px" };
const td: React.CSSProperties = { borderBottom: "1px solid #eee", padding: "6px 8px" };

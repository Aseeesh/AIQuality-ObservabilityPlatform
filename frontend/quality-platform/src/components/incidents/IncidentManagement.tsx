// Incident Management page. Mirrors the prompt's
// <IncidentManagement><ActiveIncidents/><PostMortemList/><RCAViewer/></IncidentManagement>.
// Selecting an incident shows its RCA in the viewer.
import { useState } from "react";
import type { Incident, PostMortem, RcaAnalysisView } from "../../types/dashboard";
import { sampleIncidents, samplePostMortems, sampleRca } from "../../services/sampleData";
import { Badge, Card, grid } from "../ui";

export function IncidentManagement() {
  const [selected, setSelected] = useState<string>(sampleRca.incidentId);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={grid(360)}>
        <ActiveIncidents incidents={sampleIncidents} selected={selected} onSelect={setSelected} />
        <RCAViewer analysis={sampleRca} visible={selected === sampleRca.incidentId} />
      </div>
      <PostMortemList postMortems={samplePostMortems} />
    </div>
  );
}

function ActiveIncidents({ incidents, selected, onSelect }: {
  incidents: Incident[]; selected: string; onSelect: (id: string) => void;
}) {
  return (
    <Card title={`Active incidents (${incidents.filter((i) => i.status !== "resolved").length})`}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {incidents.map((i) => (
          <div key={i.id} onClick={() => onSelect(i.id)}
            style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13,
              padding: "6px 8px", borderRadius: 6, background: i.id === selected ? "#eef2ff" : "transparent" }}>
            <Badge kind={i.severity} />
            <span style={{ fontFamily: "ui-monospace, monospace", color: "#64748b" }}>{i.id}</span>
            <span>{i.title}</span>
            <span style={{ marginLeft: "auto" }}><Badge kind={i.status} /></span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function RCAViewer({ analysis, visible }: { analysis: RcaAnalysisView; visible: boolean }) {
  return (
    <Card title="Root cause analysis">
      {!visible ? (
        <p style={{ fontSize: 13, color: "#64748b" }}>Select an incident with an RCA report.</p>
      ) : (
        <div>
          <div style={{ fontSize: 13 }}>
            <strong>{analysis.incidentId}</strong> · confidence {(analysis.confidence * 100).toFixed(0)}%
          </div>
          <p style={{ fontSize: 13, margin: "6px 0", color: "#0f172a" }}>{analysis.rootCause}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {analysis.findings.map((f, i) => (
              <div key={i} style={{ borderLeft: `3px solid ${f.severity === "critical" ? "#dc2626" : "#d97706"}`, paddingLeft: 8 }}>
                <div style={{ fontSize: 12, display: "flex", gap: 6 }}>
                  <Badge kind={f.severity} /><span style={{ color: "#64748b" }}>{f.operation}</span>
                </div>
                <div style={{ fontSize: 13 }}>{f.description}</div>
                <div style={{ fontSize: 12, color: "#475569" }}>→ {f.recommendation}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

function PostMortemList({ postMortems }: { postMortems: PostMortem[] }) {
  return (
    <Card title="Post-mortems">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {postMortems.map((p) => (
          <div key={p.incidentId} style={{ fontSize: 13 }}>
            <strong>{p.title}</strong> <span style={{ color: "#94a3b8" }}>({p.incidentId})</span>
            <div style={{ color: "#475569" }}>Root cause: {p.rootCause}</div>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
              {p.actionItems.map((a, i) => <li key={i} style={{ color: "#334155" }}>{a}</li>)}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
}

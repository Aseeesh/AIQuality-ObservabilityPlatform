// App shell: sidebar navigation + page switch + global live-feed wiring.
// A tiny Zustand-driven router (no react-router dependency) keeps the bundle lean; the active
// page is global state so deep links (e.g. an alert jumping to Monitoring) are trivial.
import type { ReactNode } from "react";
import { useDashboardStore } from "../store/useDashboardStore";
import { useLiveFeed } from "../hooks/useLiveFeed";
import { mcpClient } from "../services/mcpClient";
import type { Page } from "../types/dashboard";
import { QualityOverview } from "./dashboard/QualityOverview";
import { TracingDashboard } from "./tracing/TracingDashboard";
import { EvaluationDashboard } from "./evaluation/EvaluationDashboard";
import { MonitoringDashboard } from "./monitoring/MonitoringDashboard";
import { SLODashboard } from "./slo/SLODashboard";
import { IncidentManagement } from "./incidents/IncidentManagement";
import { FeedbackHub } from "./feedback/FeedbackHub";

const NAV: { page: Page; label: string }[] = [
  { page: "overview", label: "Quality Overview" },
  { page: "tracing", label: "Tracing Explorer" },
  { page: "evaluation", label: "Evaluation" },
  { page: "monitoring", label: "Monitoring" },
  { page: "slo", label: "SLO Dashboard" },
  { page: "incidents", label: "Incidents" },
  { page: "feedback", label: "Feedback Hub" },
];

const PAGES: Record<Page, ReactNode> = {
  overview: <QualityOverview />,
  tracing: <TracingDashboard />,
  evaluation: <EvaluationDashboard />,
  monitoring: <MonitoringDashboard />,
  slo: <SLODashboard />,
  incidents: <IncidentManagement />,
  feedback: <FeedbackHub />,
};

export function AppShell() {
  useLiveFeed(); // start the real-time metric/alert stream for the whole app
  const page = useDashboardStore((s) => s.page);
  const setPage = useDashboardStore((s) => s.setPage);
  const alerts = useDashboardStore((s) => s.alerts);
  const connected = useDashboardStore((s) => s.connected);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", minHeight: "100vh", fontFamily: "system-ui", color: "#0f172a" }}>
      <aside style={{ borderRight: "1px solid #e2e8f0", padding: 16, background: "#f8fafc" }}>
        <div style={{ fontWeight: 800, fontSize: 15, marginBottom: 2 }}>AI Quality</div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 16 }}>& Observability</div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {NAV.map((n) => (
            <button key={n.page} onClick={() => setPage(n.page)} style={{
              textAlign: "left", padding: "8px 10px", border: "none", borderRadius: 8, cursor: "pointer",
              background: page === n.page ? "#e0e7ff" : "transparent",
              fontWeight: page === n.page ? 700 : 400, fontSize: 13,
            }}>
              {n.label}
              {n.page === "monitoring" && alerts.length > 0 && (
                <span style={{ marginLeft: 6, background: "#dc2626", color: "#fff", borderRadius: 8, padding: "0 6px", fontSize: 11 }}>
                  {alerts.length}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div style={{ marginTop: 16, fontSize: 11, color: connected ? "#16a34a" : "#94a3b8" }}>
          ● live feed {connected ? "connected" : "off"}
        </div>
        <button onClick={() => mcpClient.seedDemo()} style={{ marginTop: 12, width: "100%", fontSize: 12 }}>
          Seed demo data
        </button>
      </aside>

      <main style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ marginTop: 0, fontSize: 20 }}>{NAV.find((n) => n.page === page)?.label}</h1>
        {PAGES[page]}
      </main>
    </div>
  );
}

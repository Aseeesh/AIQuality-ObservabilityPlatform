import { TracingDashboard } from "./components/tracing/TracingDashboard";

// Root component: shells the dashboard. The tracing surface (explorer, waterfall, profiling,
// RCA) is fully wired to the API; evaluation, monitoring, SLO, incident, and feedback views
// follow the same pattern.
export default function App() {
  return (
    <main style={{ fontFamily: "system-ui", padding: 24, maxWidth: 1200, margin: "0 auto", color: "#0f172a" }}>
      <h1>AI Quality &amp; Observability Platform</h1>
      <p style={{ color: "#64748b", marginTop: -8 }}>Distributed tracing &amp; debugging</p>
      <TracingDashboard />
    </main>
  );
}

import { TracesView } from "./components/tracing/TracesView";

// Root component: shells the dashboard. Tracing is wired to the live API;
// evaluation, monitoring, SLO, incident, and feedback views follow the same pattern.
export default function App() {
  return (
    <main style={{ fontFamily: "system-ui", padding: 24, maxWidth: 960, margin: "0 auto" }}>
      <h1>AI Quality &amp; Observability Platform</h1>
      <h2 style={{ marginTop: 24 }}>Traces</h2>
      <TracesView />
    </main>
  );
}

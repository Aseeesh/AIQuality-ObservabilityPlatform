import { AppShell } from "./components/AppShell";

// Root: the full quality & observability dashboard — 7 pages (overview, tracing, evaluation,
// monitoring, SLO, incidents, feedback) with Zustand state, a real-time feed, Recharts
// visualizations, and an MCP bridge for tool/agent actions.
export default function App() {
  return <AppShell />;
}

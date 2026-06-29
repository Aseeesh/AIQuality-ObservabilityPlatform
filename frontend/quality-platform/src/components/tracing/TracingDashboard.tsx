import { useState } from "react";
import { api } from "../../services/api";
import { TraceExplorer } from "./TraceExplorer";
import { TraceDetail } from "./TraceDetail";
import { PerformanceProfiling } from "./PerformanceProfiling";

type Tab = "explorer" | "profiling";

// Top-level tracing & debugging surface: an Explorer tab (trace list + detail/waterfall/RCA)
// and a Profiling tab (latency distribution + slowest traces). A "Seed demo data" button
// populates the in-memory store so the UI is explorable without a live workload.
export function TracingDashboard() {
  const [tab, setTab] = useState<Tab>("explorer");
  const [selected, setSelected] = useState<string>();
  const [refreshKey, setRefreshKey] = useState(0);
  const [seeding, setSeeding] = useState(false);

  async function seed() {
    setSeeding(true);
    try {
      const { seeded } = await api.seedDemo();
      setSelected(seeded[seeded.length - 1]); // jump to the failing trace
      setRefreshKey((k) => k + 1);
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <TabButton active={tab === "explorer"} onClick={() => setTab("explorer")}>Explorer</TabButton>
        <TabButton active={tab === "profiling"} onClick={() => setTab("profiling")}>Profiling</TabButton>
        <button onClick={seed} disabled={seeding} style={{ marginLeft: "auto" }}>
          {seeding ? "Seeding…" : "Seed demo data"}
        </button>
      </div>

      {tab === "explorer" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <TraceExplorer key={refreshKey} selectedTraceId={selected} onSelect={setSelected} />
          {selected && (
            <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: 14 }}>
              <TraceDetail key={selected} traceId={selected} />
            </div>
          )}
        </div>
      ) : (
        <PerformanceProfiling
          key={refreshKey}
          onSelectTrace={(id) => {
            setSelected(id);
            setTab("explorer");
          }}
        />
      )}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        border: "none",
        borderBottom: active ? "2px solid #4f46e5" : "2px solid transparent",
        background: "transparent",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

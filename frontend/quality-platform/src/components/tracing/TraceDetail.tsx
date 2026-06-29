import { useEffect, useState } from "react";
import { api } from "../../services/api";
import type { TraceRootCauseAnalysis, TraceSpan } from "../../types/span";
import { fmtDuration } from "./spanUtils";
import { WaterfallChart } from "./WaterfallChart";
import { SpanDetails } from "./SpanDetails";
import { RootCauseAnalysis } from "./RootCauseAnalysis";

// Trace detail view: loads the full span tree + RCA for a trace and lays out the waterfall
// alongside an inspector (selected span details) and the root-cause panel.
export function TraceDetail({ traceId }: { traceId: string }) {
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [rca, setRca] = useState<TraceRootCauseAnalysis | null>(null);
  const [selected, setSelected] = useState<string>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelected(undefined);
    Promise.all([api.getTraceSpans(traceId), api.getRca(traceId)])
      .then(([s, r]) => {
        setSpans(s);
        setRca(r);
        // Default selection: the root-cause span if any, else the root span.
        setSelected(r.primaryRootCauseSpanId ?? s.find((x) => !x.parentSpanId)?.spanId ?? s[0]?.spanId);
        setError(null);
      })
      .catch((e) => setError((e as Error).message));
  }, [traceId]);

  if (error) return <p style={{ color: "crimson" }}>Failed to load trace: {error}</p>;
  if (spans.length === 0) return <p>Loading trace…</p>;

  const total = spans.find((s) => !s.parentSpanId)?.durationMs ?? Math.max(...spans.map((s) => s.durationMs));
  const selectedSpan = spans.find((s) => s.spanId === selected);

  return (
    <div>
      <div style={{ fontSize: 13, color: "#475569", marginBottom: 8 }}>
        Trace <code>{traceId.slice(0, 12)}</code> · {spans.length} spans · {fmtDuration(total)}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16, alignItems: "start" }}>
        <div>
          <h3 style={hdr}>Waterfall</h3>
          <WaterfallChart spans={spans} selectedSpanId={selected} onSelect={setSelected} />

          {rca && (
            <>
              <h3 style={{ ...hdr, marginTop: 18 }}>Root Cause Analysis</h3>
              <RootCauseAnalysis rca={rca} onSelectSpan={setSelected} />
            </>
          )}
        </div>

        <div style={{ position: "sticky", top: 8, border: "1px solid #e2e8f0", borderRadius: 8, padding: 12 }}>
          <h3 style={hdr}>Span Details</h3>
          {selectedSpan ? <SpanDetails span={selectedSpan} /> : <p style={{ fontSize: 13 }}>Select a span.</p>}
        </div>
      </div>
    </div>
  );
}

const hdr: React.CSSProperties = { fontSize: 14, margin: "0 0 8px" };

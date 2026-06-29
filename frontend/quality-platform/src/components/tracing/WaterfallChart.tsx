import type { TraceSpan } from "../../types/span";
import { fmtDuration, kindColor, kindLabel, spanDepths, statusColor } from "./spanUtils";

// Waterfall visualization of a trace's span tree.
//
// Design: spans share a single time axis (trace start -> trace end). Each row is a span,
// indented by its depth in the tree; the coloured bar is positioned by start offset and
// sized by duration, so nesting and relative cost are both readable at a glance. Clicking a
// row selects the span for the detail panel. We deliberately render with absolute-positioned
// divs (no chart lib) to keep the bundle small and the layout fully controllable.
export function WaterfallChart({
  spans,
  selectedSpanId,
  onSelect,
}: {
  spans: TraceSpan[];
  selectedSpanId?: string;
  onSelect: (spanId: string) => void;
}) {
  if (spans.length === 0) return <p>No spans.</p>;

  // Time axis: earliest start to latest end across all spans.
  const starts = spans.map((s) => new Date(s.startTime).getTime());
  const ends = spans.map((s) => new Date(s.endTime ?? s.startTime).getTime());
  const t0 = Math.min(...starts);
  const t1 = Math.max(...ends);
  const span = Math.max(1, t1 - t0);

  const depth = spanDepths(spans);
  // Render parents before children, then by start time, for a natural top-down cascade.
  const ordered = [...spans].sort(
    (a, b) => (depth.get(a.spanId)! - depth.get(b.spanId)!) ||
      new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {ordered.map((s) => {
        const start = new Date(s.startTime).getTime();
        const dur = new Date(s.endTime ?? s.startTime).getTime() - start;
        const left = ((start - t0) / span) * 100;
        const width = Math.max(0.5, (dur / span) * 100);
        const selected = s.spanId === selectedSpanId;
        return (
          <div
            key={s.spanId}
            onClick={() => onSelect(s.spanId)}
            style={{
              display: "grid",
              gridTemplateColumns: "260px 1fr",
              gap: 8,
              cursor: "pointer",
              background: selected ? "#eef2ff" : "transparent",
              borderRadius: 4,
              padding: "2px 4px",
            }}
          >
            {/* Label column, indented by depth */}
            <div style={{ paddingLeft: depth.get(s.spanId)! * 14, display: "flex", alignItems: "center", gap: 6, overflow: "hidden" }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: kindColor(s.aiContext?.kind), flex: "none" }} />
              <span style={{ fontSize: 13, whiteSpace: "nowrap", textOverflow: "ellipsis", overflow: "hidden" }}>
                {s.operationName}
              </span>
            </div>
            {/* Bar column */}
            <div style={{ position: "relative", height: 20, background: "#f1f5f9", borderRadius: 4 }}>
              <div
                title={`${kindLabel(s.aiContext?.kind)} · ${fmtDuration(s.durationMs)}`}
                style={{
                  position: "absolute",
                  left: `${left}%`,
                  width: `${width}%`,
                  top: 0,
                  height: "100%",
                  background: kindColor(s.aiContext?.kind),
                  border: s.status === 2 ? "2px solid " + statusColor(2) : "none",
                  borderRadius: 4,
                  boxSizing: "border-box",
                }}
              />
              <span style={{ position: "absolute", left: `calc(${Math.min(left, 80)}% + 4px)`, fontSize: 11, lineHeight: "20px", color: "#334155" }}>
                {fmtDuration(s.durationMs)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

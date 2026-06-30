// Small presentational primitives shared across dashboard pages (kept dependency-free and
// inline-styled to match the existing tracing UI).
import type { CSSProperties, ReactNode } from "react";

export function Card({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section style={card}>
      {(title || right) && (
        <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
          {title && <h3 style={{ margin: 0, fontSize: 14 }}>{title}</h3>}
          {right && <div style={{ marginLeft: "auto" }}>{right}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div style={{ background: "#f8fafc", borderRadius: 8, padding: "10px 14px", minWidth: 110 }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: color ?? "#0f172a" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#64748b" }}>{label}</div>
    </div>
  );
}

const SEV_COLOR: Record<string, string> = {
  P1: "#dc2626", P2: "#ea580c", P3: "#d97706", P4: "#2563eb",
  critical: "#dc2626", warning: "#d97706", info: "#2563eb",
  open: "#ea580c", escalated: "#dc2626", resolved: "#16a34a",
  positive: "#16a34a", neutral: "#64748b", negative: "#dc2626",
};

export function Badge({ kind }: { kind: string }) {
  const color = SEV_COLOR[kind] ?? "#64748b";
  return (
    <span style={{ background: color + "22", color, borderRadius: 10, padding: "1px 8px", fontSize: 12, fontWeight: 600 }}>
      {kind}
    </span>
  );
}

export const grid = (min: number): CSSProperties => ({
  display: "grid", gap: 16, gridTemplateColumns: `repeat(auto-fit, minmax(${min}px, 1fr))`,
});

const card: CSSProperties = {
  border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fff",
};

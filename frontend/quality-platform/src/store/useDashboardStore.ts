// Global dashboard state (Zustand). Holds the active page, the rolling live-metric buffers
// (fed by the WebSocket/live feed), and the alert notifications. Kept deliberately small —
// page data is fetched by the pages themselves; this store only holds cross-cutting,
// real-time state that many components observe.
import { create } from "zustand";
import type { AlertNotification, LiveMetric, Page } from "../types/dashboard";

const MAX_POINTS = 60; // rolling window per metric

interface DashboardState {
  page: Page;
  setPage: (p: Page) => void;

  // metric name -> rolling series of recent ticks
  liveMetrics: Record<string, LiveMetric[]>;
  pushMetric: (m: LiveMetric) => void;

  alerts: AlertNotification[];
  pushAlert: (a: AlertNotification) => void;
  dismissAlert: (id: string) => void;

  connected: boolean;
  setConnected: (c: boolean) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  page: "overview",
  setPage: (page) => set({ page }),

  liveMetrics: {},
  pushMetric: (m) =>
    set((state) => {
      const series = state.liveMetrics[m.name] ?? [];
      const next = [...series, m].slice(-MAX_POINTS);
      return { liveMetrics: { ...state.liveMetrics, [m.name]: next } };
    }),

  alerts: [],
  pushAlert: (a) => set((state) => ({ alerts: [a, ...state.alerts].slice(0, 20) })),
  dismissAlert: (id) => set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),

  connected: false,
  setConnected: (connected) => set({ connected }),
}));

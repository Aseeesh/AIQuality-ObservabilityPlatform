// Real-time metric feed.
//
// Connects to a WebSocket (VITE_WS_URL) that streams {name, value, isAnomaly} ticks and an
// occasional alert. Because the demo backend has no WS endpoint, it falls back to a simulated
// generator so the Monitoring/Overview pages still update live — the component code is
// identical either way, which is the point: swap the URL in and real data flows.
import { useEffect, useRef } from "react";
import { useDashboardStore } from "../store/useDashboardStore";
import type { AlertNotification, LiveMetric } from "../types/dashboard";

const WS_URL = import.meta.env.VITE_WS_URL as string | undefined;
const METRICS = ["quality-score", "latency-ms", "error-rate"];

export function useLiveFeed() {
  const pushMetric = useDashboardStore((s) => s.pushMetric);
  const pushAlert = useDashboardStore((s) => s.pushAlert);
  const setConnected = useDashboardStore((s) => s.setConnected);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    // Preferred path: a real WebSocket stream.
    if (WS_URL) {
      const ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "metric") pushMetric(msg.data as LiveMetric);
          if (msg.type === "alert") pushAlert(msg.data as AlertNotification);
        } catch {
          /* ignore malformed frames */
        }
      };
      return () => ws.close();
    }

    // Fallback: simulate a live stream on a 1s interval.
    setConnected(true);
    const baselines: Record<string, number> = { "quality-score": 0.9, "latency-ms": 800, "error-rate": 0.01 };
    timer.current = window.setInterval(() => {
      for (const name of METRICS) {
        const base = baselines[name];
        // Occasional injected spike to demonstrate anomaly highlighting + alerts.
        const spike = Math.random() < 0.05;
        const noise = (Math.random() - 0.5) * base * 0.1;
        const value = spike
          ? name === "quality-score" ? base * 0.3 : base * 3
          : base + noise;
        const isAnomaly = spike;
        pushMetric({ name, value: round(value), t: Date.now(), isAnomaly });
        if (isAnomaly) {
          pushAlert({
            id: `${name}-${Date.now()}`,
            severity: name === "error-rate" ? "P1" : "P2",
            metric: name,
            message: `${name} anomaly: ${round(value)}`,
            t: Date.now(),
          });
        }
      }
    }, 1000);

    return () => {
      if (timer.current) window.clearInterval(timer.current);
      setConnected(false);
    };
  }, [pushMetric, pushAlert, setConnected]);
}

const round = (n: number) => Math.round(n * 1000) / 1000;

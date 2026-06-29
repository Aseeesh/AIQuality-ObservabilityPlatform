import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config for the React 19.2 quality dashboard.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: true },
});

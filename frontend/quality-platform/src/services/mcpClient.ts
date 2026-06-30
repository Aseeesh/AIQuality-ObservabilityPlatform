// MCP bridge for the dashboard.
//
// The MCP server (python-services/mcp-integration) speaks the MCP protocol over stdio, not
// HTTP, so the browser can't call it directly. This client models the dashboard->MCP bridge:
// in production it would POST to a thin HTTP gateway that forwards to the MCP server's
// ToolRegistry. Here it maps the few tools the dashboard needs onto the .NET REST API where
// an equivalent endpoint exists, and otherwise returns a clearly-labelled stub so the UI is
// fully interactive offline.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:5099";

export interface McpToolResult {
  tool: string;
  ok: boolean;
  result: unknown;
  note?: string;
}

async function tryJson(url: string, init?: RequestInit): Promise<unknown | null> {
  try {
    const res = await fetch(url, init);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export const mcpClient = {
  // Run a quality evaluation via the batch endpoint (single-item batch).
  async evaluateOutput(prompt: string, output: string, context = ""): Promise<McpToolResult> {
    const result = await tryJson(`${BASE}/api/evaluation/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataset: "dashboard-adhoc",
        environment: "staging",
        items: [{ prompt, output, context }],
      }),
    });
    return result
      ? { tool: "evaluate_output", ok: true, result }
      : { tool: "evaluate_output", ok: false, result: null, note: "API offline" };
  },

  // Generate an improvement plan (agent-driven action) for a dataset.
  async runImprovementAgent(dataset: string): Promise<McpToolResult> {
    const result = await tryJson(`${BASE}/api/improvement/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, environment: "staging" }),
    });
    return result
      ? { tool: "improvement_agent", ok: true, result }
      : { tool: "improvement_agent", ok: false, result: null, note: "API offline" };
  },

  // Seed demo data across the platform so the dashboard has something to show.
  async seedDemo(): Promise<McpToolResult> {
    const spans = await tryJson(`${BASE}/api/spans/demo`, { method: "POST" });
    const evalDemo = await tryJson(`${BASE}/api/improvement/demo`, { method: "POST" });
    return { tool: "seed_demo", ok: !!(spans || evalDemo), result: { spans, evalDemo } };
  },
};

// Typed client for the Agent-ROI REST API.

export type Dimension = "topic" | "tool" | "model";

export interface Rollup {
  key: string;
  interactions: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  cost_usd: number;
  total_tokens: number;
  estimated: boolean;
}

export interface TopicBreakdown {
  topic: string;
  total: Rollup;
  by_tool: Rollup[];
  by_model: Rollup[];
}

export interface ModelPricing {
  model: string;
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
}

const BACKEND_DOWN =
  "Can't reach the Agent-ROI backend. Start it with `agent-roi serve`, " +
  "or open the app it serves at http://127.0.0.1:8000 instead of the dev server.";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    // Network-level failure (e.g. dev server can't reach the API backend).
    throw new Error(BACKEND_DOWN);
  }
  if (res.status >= 500) {
    // The proxy returns 500 when the backend isn't running.
    throw new Error(BACKEND_DOWN);
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string>) => {
  const s = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== "")
  ).toString();
  return s ? `?${s}` : "";
};

export const api = {
  report: (groupBy: Dimension, since: string) =>
    request<Rollup[]>(`/api/report${qs({ group_by: groupBy, since })}`),

  topic: (topic: string, since: string) =>
    request<TopicBreakdown>(`/api/report/topic/${encodeURIComponent(topic)}${qs({ since })}`),

  pricing: () => request<ModelPricing[]>("/api/pricing"),

  ingest: () => request<{ ingested: number }>("/api/ingest", { method: "POST" }),
  classify: () => request<{ classified: number }>("/api/classify", { method: "POST" }),
};

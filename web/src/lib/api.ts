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

async function json<T>(res: Response): Promise<T> {
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
    fetch(`/api/report${qs({ group_by: groupBy, since })}`).then(json<Rollup[]>),

  topic: (topic: string, since: string) =>
    fetch(`/api/report/topic/${encodeURIComponent(topic)}${qs({ since })}`).then(
      json<TopicBreakdown>
    ),

  pricing: () => fetch("/api/pricing").then(json<ModelPricing[]>),

  ingest: () => fetch("/api/ingest", { method: "POST" }).then(json<{ ingested: number }>),
  classify: () => fetch("/api/classify", { method: "POST" }).then(json<{ classified: number }>),
};

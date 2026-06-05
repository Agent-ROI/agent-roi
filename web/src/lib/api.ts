// Typed client for the Agent-ROI REST API.

export interface TopicRollup {
  topic: string;
  interactions: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  cost_usd: number;
  total_tokens: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  topics: () => fetch("/api/report/topics").then(json<TopicRollup[]>),
  ingest: () => fetch("/api/ingest", { method: "POST" }).then(json<{ ingested: number }>),
  classify: () => fetch("/api/classify", { method: "POST" }).then(json<{ classified: number }>),
};

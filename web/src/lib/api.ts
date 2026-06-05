import i18n from "../i18n";

// Typed client for the Agent-ROI REST API.

export type Dimension = "topic" | "tool" | "model" | "project";

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
  effective_from: string;
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
}

export interface SessionSummary {
  session_id: string;
  topic: string;
  project: string;
  tools: string[];
  models: string[];
  started: string;
  ended: string;
  interactions: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  total_tokens: number;
  cost_usd: number;
  estimated: boolean;
}

export interface InteractionView {
  id: string;
  tool: string;
  model: string;
  timestamp: string;
  total_tokens: number;
  cost_usd: number;
  estimated: boolean;
  summary: string;
}

export interface SessionDetail {
  session: SessionSummary;
  interactions: InteractionView[];
}

export interface CollectorStatus {
  name: string;
  tool: string;
  available: boolean;
  search_paths: string[];
  log_files: number;
  interactions: number;
  tokens: number;
  cost_usd: number;
  note: string;
}

export interface Sources {
  platform: string;
  collectors: CollectorStatus[];
}

export interface TimeSeriesPoint {
  date: string;
  interactions: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  cost_usd: number;
  total_tokens: number;
}

export interface TimeSeriesSplitRow {
  date: string;
  values: Record<string, number>;
  cost_usd: number;
  interactions: number;
}

export interface TimeSeriesBundle {
  granularity: string;
  totals: TimeSeriesPoint[];
  by_tool: TimeSeriesSplitRow[];
  by_model: TimeSeriesSplitRow[];
  tool_keys: string[];
  model_keys: string[];
}

export interface WindowParams {
  since?: string;
  until?: string;
  granularity?: string;
}

export interface BudgetPeriodStatus {
  period: "day" | "week" | "month";
  start: string;
  spent_usd: number;
  limit_usd: number | null;
  pct: number | null;
  over: boolean;
  remaining_usd: number | null;
}

export interface BudgetStatus {
  periods: BudgetPeriodStatus[];
  any_over: boolean;
}

export interface BudgetSettings {
  daily_usd: number | null;
  weekly_usd: number | null;
  monthly_usd: number | null;
}

export interface ConfigInfo {
  config_path: string;
  db_path: string;
  classifier: {
    provider: string;
    similarity_threshold: number;
    label_terms: number;
  };
  collectors: {
    enabled: string[];
  };
  budget: BudgetSettings;
}

function backendDownMessage(): string {
  return i18n.t("errors.backendDown");
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    // Network-level failure (e.g. dev server can't reach the API backend).
    throw new Error(backendDownMessage());
  }
  if (res.status >= 500) {
    // The proxy returns 500 when the backend isn't running.
    throw new Error(backendDownMessage());
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
  report: (groupBy: Dimension, window: WindowParams = {}) =>
    request<Rollup[]>(
      `/api/report${qs({ group_by: groupBy, since: window.since ?? "", until: window.until ?? "" })}`
    ),

  topic: (topic: string, window: WindowParams = {}) =>
    request<TopicBreakdown>(
      `/api/report/topic/${encodeURIComponent(topic)}${qs({
        since: window.since ?? "",
        until: window.until ?? "",
      })}`
    ),

  pricing: () => request<ModelPricing[]>("/api/pricing"),

  budget: () => request<BudgetStatus>("/api/budget"),

  sessions: (topic: string, window: WindowParams = {}, search?: string) =>
    request<SessionSummary[]>(
      `/api/sessions${qs({
        topic,
        since: window.since ?? "",
        until: window.until ?? "",
        search: search ?? "",
      })}`
    ),

  session: (id: string) =>
    request<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}`),

  sources: () => request<Sources>("/api/sources"),

  timeseries: (window: WindowParams = {}) =>
    request<TimeSeriesBundle>(
      `/api/timeseries${qs({
        since: window.since ?? "",
        until: window.until ?? "",
        granularity: window.granularity ?? "day",
      })}`
    ),

  ingest: () => request<{ ingested: number }>("/api/ingest", { method: "POST" }),
  classify: () => request<{ classified: number }>("/api/classify", { method: "POST" }),
  refresh: () =>
    request<{ ingested: number; classified: number }>("/api/refresh", { method: "POST" }),

  getConfig: () => request<ConfigInfo>("/api/config"),

  updateConfig: (body: {
    classifier?: Partial<ConfigInfo["classifier"]>;
    collectors?: Partial<ConfigInfo["collectors"]>;
    budget?: Partial<BudgetSettings>;
  }) =>
    request<ConfigInfo>("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};

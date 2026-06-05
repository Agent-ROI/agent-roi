import type { InteractionView } from "./api";

/** One group of model calls that share the same captured summary text. */
export interface CallGroup {
  summary: string;
  count: number;
  totalTokens: number;
  costUsd: number;
  estimated: boolean;
  firstAt: string;
  lastAt: string;
  tool: string;
  model: string;
  items: InteractionView[];
}

/** Group identical summaries so repeated agent loops read as one pattern. */
export function groupCalls(items: InteractionView[]): CallGroup[] {
  const map = new Map<string, CallGroup>();

  for (const item of items) {
    const key = item.summary || "";
    let group = map.get(key);
    if (!group) {
      group = {
        summary: key,
        count: 0,
        totalTokens: 0,
        costUsd: 0,
        estimated: false,
        firstAt: item.timestamp,
        lastAt: item.timestamp,
        tool: item.tool,
        model: item.model,
        items: [],
      };
      map.set(key, group);
    }
    group.count += 1;
    group.totalTokens += item.total_tokens;
    group.costUsd += item.cost_usd;
    group.estimated = group.estimated || item.estimated;
    if (item.timestamp < group.firstAt) group.firstAt = item.timestamp;
    if (item.timestamp > group.lastAt) group.lastAt = item.timestamp;
    group.items.push(item);
  }

  return [...map.values()].sort((a, b) => b.costUsd - a.costUsd);
}

/** Snippets the classifier actually sees (matches backend: chrono, max 8 unique). */
export function classificationSnippets(items: InteractionView[], max = 8): string[] {
  const sorted = [...items].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of sorted) {
    if (item.summary && !seen.has(item.summary)) {
      seen.add(item.summary);
      out.push(item.summary);
      if (out.length >= max) break;
    }
  }
  return out;
}

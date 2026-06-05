import type { TimeSeriesBundle, TimeSeriesSplitRow } from "./api";

export function totalsChartData(bundle: TimeSeriesBundle) {
  return bundle.totals.map((p) => ({
    date: p.date,
    tokens: p.total_tokens,
    cost: Number(p.cost_usd.toFixed(4)),
    input: p.input_tokens,
    output: p.output_tokens,
    interactions: p.interactions,
  }));
}

export function splitChartData(rows: TimeSeriesSplitRow[], keys: string[]) {
  return rows.map((row) => {
    const point: Record<string, string | number> = { date: row.date };
    for (const key of keys) {
      point[key] = row.values[key] ?? 0;
    }
    return point;
  });
}

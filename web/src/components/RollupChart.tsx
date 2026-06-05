import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { Rollup, Dimension } from "../lib/api";
import { fmtUsd } from "../lib/format";

interface Props {
  rows: Rollup[];
  dimension: Dimension;
}

// Top rows by cost, so the most expensive items stand out.
export function RollupChart({ rows, dimension }: Props) {
  const data = rows
    .slice()
    .sort((a, b) => b.cost_usd - a.cost_usd)
    .slice(0, 10)
    .map((r) => ({ key: r.key, cost: Number(r.cost_usd.toFixed(4)) }));

  return (
    <section className="card">
      <h2>Cost by {dimension} (top 10)</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#23252a" />
          <XAxis type="number" stroke="#8a8f98" fontSize={12} tickFormatter={(v) => fmtUsd(v)} />
          <YAxis type="category" dataKey="key" width={140} stroke="#8a8f98" fontSize={12} />
          <Tooltip
            cursor={{ fill: "rgba(94,106,210,0.08)" }}
            formatter={(v: number) => fmtUsd(v)}
            contentStyle={{
              background: "#141516",
              border: "1px solid #34343a",
              borderRadius: 8,
              color: "#f7f8f8",
            }}
          />
          <Bar dataKey="cost" fill="#5e6ad2" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}

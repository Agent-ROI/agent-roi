import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TopicRollup } from "../lib/api";
import { fmtUsd } from "../lib/format";

interface Props {
  topics: TopicRollup[];
}

// Top topics by cost, so the most expensive subjects stand out.
export function TopicChart({ topics }: Props) {
  const data = topics
    .slice()
    .sort((a, b) => b.cost_usd - a.cost_usd)
    .slice(0, 10)
    .map((t) => ({ topic: t.topic, cost: Number(t.cost_usd.toFixed(4)) }));

  return (
    <section className="card">
      <h2>Cost by Topic (top 10)</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
          <XAxis type="number" stroke="#888" tickFormatter={(v) => fmtUsd(v)} />
          <YAxis type="category" dataKey="topic" width={140} stroke="#888" />
          <Tooltip
            formatter={(v: number) => fmtUsd(v)}
            contentStyle={{ background: "#1a1a2e", border: "1px solid #333" }}
          />
          <Bar dataKey="cost" fill="#7c5cff" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}

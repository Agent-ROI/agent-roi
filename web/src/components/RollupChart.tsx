import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useTranslation } from "react-i18next";
import type { Rollup, Dimension } from "../lib/api";
import { fmtUsd } from "../lib/format";

interface Props {
  rows: Rollup[];
  dimension: Dimension;
}

export function RollupChart({ rows, dimension }: Props) {
  const { t } = useTranslation();
  const dimLabel = t(`dimension.${dimension}`);
  const data = rows
    .slice()
    .sort((a, b) => b.cost_usd - a.cost_usd)
    .slice(0, 10)
    .map((r) => ({ key: r.key, cost: Number(r.cost_usd.toFixed(4)) }));

  return (
    <section className="card">
      <h2>{t("chart.costByTop", { dimension: dimLabel })}</h2>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e3df" />
          <XAxis type="number" stroke="#787671" fontSize={12} tickFormatter={(v) => fmtUsd(v)} />
          <YAxis type="category" dataKey="key" width={140} stroke="#787671" fontSize={12} />
          <Tooltip
            cursor={{ fill: "rgba(86,69,212,0.06)" }}
            formatter={(v: number) => fmtUsd(v)}
            contentStyle={{
              background: "#ffffff",
              border: "1px solid #e5e3df",
              borderRadius: 8,
              color: "#1a1a1a",
              boxShadow: "rgba(15, 15, 15, 0.08) 0px 4px 12px 0px",
            }}
          />
          <Bar dataKey="cost" fill="#5645d4" radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}

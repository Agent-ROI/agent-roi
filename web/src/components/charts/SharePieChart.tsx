import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { useTranslation } from "react-i18next";
import type { Rollup } from "../../lib/api";
import { chartTooltipStyle, seriesColor } from "../../lib/chartTheme";
import { fmtTokens } from "../../lib/format";

interface Props {
  title: string;
  rows: Rollup[];
  height?: number;
}

export function SharePieChart({ title, rows, height = 280 }: Props) {
  const { t } = useTranslation();
  const data = rows
    .slice()
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 8)
    .map((r) => ({ name: r.key, value: r.total_tokens }));

  if (!data.length) {
    return (
      <section className="card chart-card">
        <h2>{title}</h2>
        <p className="muted">{t("app.noData")}</p>
      </section>
    );
  }

  return (
    <section className="card chart-card">
      <h2>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={58}
            outerRadius={96}
            paddingAngle={2}
            isAnimationActive={false}
          >
            {data.map((entry, i) => (
              <Cell key={entry.name} fill={seriesColor(entry.name, i)} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => fmtTokens(v)} contentStyle={chartTooltipStyle} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </section>
  );
}

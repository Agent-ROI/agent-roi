import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { useTranslation } from "react-i18next";
import { chartTooltipStyle, seriesColor } from "../../lib/chartTheme";
import { fmtTokens } from "../../lib/format";

interface Props {
  title: string;
  data: Record<string, string | number>[];
  keys: string[];
  height?: number;
}

export function StackedAreaChart({ title, data, keys, height = 300 }: Props) {
  const { t } = useTranslation();

  return (
    <section className="card chart-card">
      <h2>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ left: 8, right: 16, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e3df" />
          <XAxis dataKey="date" stroke="#787671" fontSize={11} tickMargin={8} />
          <YAxis
            stroke="#787671"
            fontSize={11}
            tickFormatter={(v) => fmtTokens(Number(v))}
            width={72}
          />
          <Tooltip formatter={(v: number) => fmtTokens(v)} contentStyle={chartTooltipStyle} />
          <Legend />
          {keys.map((key, i) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={key === "other" ? t("chart.other") : key}
              stackId="1"
              stroke={seriesColor(key, i)}
              fill={seriesColor(key, i)}
              fillOpacity={0.35}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </section>
  );
}

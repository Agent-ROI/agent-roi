import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { chartTooltipStyle } from "../../lib/chartTheme";

interface Series {
  key: string;
  label: string;
  color: string;
}

interface Props {
  title: string;
  data: Record<string, string | number>[];
  xKey?: string;
  series: Series[];
  valueFormatter: (value: number) => string;
  height?: number;
}

export function TrendLineChart({
  title,
  data,
  xKey = "date",
  series,
  valueFormatter,
  height = 280,
}: Props) {
  return (
    <section className="card chart-card">
      <h2>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ left: 8, right: 16, top: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e3df" />
          <XAxis dataKey={xKey} stroke="#787671" fontSize={11} tickMargin={8} />
          <YAxis
            stroke="#787671"
            fontSize={11}
            tickFormatter={(v) => valueFormatter(Number(v))}
            width={72}
          />
          <Tooltip
            formatter={(v) => valueFormatter(v as number)}
            contentStyle={chartTooltipStyle}
          />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

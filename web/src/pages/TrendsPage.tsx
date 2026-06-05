import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type TimeSeriesBundle } from "../lib/api";
import { fmtUsd } from "../lib/format";
import { splitChartData, totalsChartData } from "../lib/timeseriesView";
import { TrendLineChart } from "../components/charts/TrendLineChart";
import { StackedAreaChart } from "../components/charts/StackedAreaChart";

interface Props {
  since: string;
}

export function TrendsPage({ since }: Props) {
  const { t } = useTranslation();
  const [series, setSeries] = useState<TimeSeriesBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api
      .timeseries(since)
      .then((data) => active && setSeries(data))
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [since, t]);

  const totals = series ? totalsChartData(series) : [];
  const byTool = series ? splitChartData(series.by_tool, series.tool_keys) : [];
  const byModel = series ? splitChartData(series.by_model, series.model_keys) : [];

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.trends")}</h2>
        <p className="muted">{t("pages.trendsHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : !series?.totals.length ? (
        <p className="muted">{t("app.noData")}</p>
      ) : (
        <>
          <TrendLineChart
            title={t("chart.tokenTrend")}
            data={totals}
            series={[{ key: "tokens", label: t("table.tokens"), color: "#5645d4" }]}
            valueFormatter={(v) => `${Math.round(v).toLocaleString()}`}
            height={320}
          />
          <div className="chart-grid two-col">
            <TrendLineChart
              title={t("chart.costTrend")}
              data={totals}
              series={[{ key: "cost", label: t("table.cost"), color: "#dd5b00" }]}
              valueFormatter={(v) => fmtUsd(v)}
            />
            <TrendLineChart
              title={t("chart.interactionsTrend")}
              data={totals}
              series={[
                {
                  key: "interactions",
                  label: t("stats.interactions"),
                  color: "#0075de",
                },
              ]}
              valueFormatter={(v) => `${Math.round(v).toLocaleString()}`}
            />
          </div>
          <div className="chart-grid two-col">
            <StackedAreaChart
              title={t("chart.tokensByTool")}
              data={byTool}
              keys={series.tool_keys}
            />
            <StackedAreaChart
              title={t("chart.tokensByModel")}
              data={byModel}
              keys={series.model_keys}
            />
          </div>
          <TrendLineChart
            title={t("chart.ioTrend")}
            data={totals}
            series={[
              { key: "input", label: t("table.input"), color: "#5645d4" },
              { key: "output", label: t("table.output"), color: "#1aae39" },
            ]}
            valueFormatter={(v) => `${Math.round(v).toLocaleString()}`}
            height={300}
          />
        </>
      )}
    </div>
  );
}

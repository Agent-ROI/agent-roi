import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Rollup, type TimeSeriesBundle } from "../lib/api";
import type { DateFilter, Granularity } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { fmtUsd } from "../lib/format";
import { totalsChartData } from "../lib/timeseriesView";
import { StatsCards } from "../components/StatsCards";
import { TrendLineChart } from "../components/charts/TrendLineChart";
import { SharePieChart } from "../components/charts/SharePieChart";
import { RollupTable } from "../components/RollupTable";

interface Props {
  filter: DateFilter;
  granularity: Granularity;
  onDrillTopic: (topic: string) => void;
}

export function OverviewPage({ filter, granularity, onDrillTopic }: Props) {
  const { t } = useTranslation();
  const [topics, setTopics] = useState<Rollup[]>([]);
  const [tools, setTools] = useState<Rollup[]>([]);
  const [series, setSeries] = useState<TimeSeriesBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (rangeInvalid(filter)) {
      setLoading(false);
      setError(null);
      setTopics([]);
      setTools([]);
      setSeries(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    const window = { since: filter.since, until: filter.until, granularity };
    Promise.all([
      api.report("topic", window),
      api.report("tool", window),
      api.timeseries(window),
    ])
      .then(([topicRows, toolRows, ts]) => {
        if (!active) return;
        setTopics(topicRows);
        setTools(toolRows);
        setSeries(ts);
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [filter, granularity, t]);

  const chartData = series ? totalsChartData(series) : [];

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.overview")}</h2>
        <p className="muted">{t("pages.overviewHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : (
        <>
          <StatsCards rows={topics} extraLabel={t("dimension.topic")} />
          <div className="chart-grid two-col">
            <TrendLineChart
              title={t("chart.tokenTrend")}
              data={chartData}
              series={[{ key: "tokens", label: t("table.tokens"), color: "#5645d4" }]}
              valueFormatter={(v) => `${Math.round(v).toLocaleString()}`}
            />
            <TrendLineChart
              title={t("chart.costTrend")}
              data={chartData}
              series={[{ key: "cost", label: t("table.cost"), color: "#dd5b00" }]}
              valueFormatter={(v) => fmtUsd(v)}
            />
          </div>
          <div className="chart-grid two-col">
            <SharePieChart title={t("chart.toolShare")} rows={tools} />
            <TrendLineChart
              title={t("chart.ioTrend")}
              data={chartData}
              series={[
                { key: "input", label: t("table.input"), color: "#5645d4" },
                { key: "output", label: t("table.output"), color: "#1aae39" },
              ]}
              valueFormatter={(v) => `${Math.round(v).toLocaleString()}`}
            />
          </div>
          <RollupTable
            rows={topics.slice(0, 8)}
            dimension="topic"
            onDrill={onDrillTopic}
            title={t("pages.topTopics")}
          />
        </>
      )}
    </div>
  );
}

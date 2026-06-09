import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  api,
  type BudgetStatus,
  type CompositionBundle,
  type Rollup,
  type TimeSeriesBundle,
  type TopicROI,
} from "../lib/api";
import type { DateFilter, Granularity } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { fmtUsd } from "../lib/format";
import { totalsChartData } from "../lib/timeseriesView";
import { BudgetPanel } from "../components/BudgetPanel";
import { StatsCards } from "../components/StatsCards";
import { TrendLineChart } from "../components/charts/TrendLineChart";
import { SharePieChart } from "../components/charts/SharePieChart";
import { RollupTable } from "../components/RollupTable";
import { CompositionCard } from "../components/CompositionCard";
import type { PageId } from "../components/layout/Sidebar";

interface Props {
  filter: DateFilter;
  granularity: Granularity;
  onDrillTopic: (topic: string) => void;
  onNavigate?: (page: PageId) => void;
  reloadKey?: number;
}

export function OverviewPage({
  filter,
  granularity,
  onDrillTopic,
  onNavigate,
  reloadKey,
}: Props) {
  const { t } = useTranslation();
  const [topics, setTopics] = useState<Rollup[]>([]);
  const [tools, setTools] = useState<Rollup[]>([]);
  const [series, setSeries] = useState<TimeSeriesBundle | null>(null);
  const [composition, setComposition] = useState<CompositionBundle | null>(null);
  const [roi, setRoi] = useState<TopicROI[]>([]);
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (rangeInvalid(filter)) {
      setLoading(false);
      setError(null);
      setTopics([]);
      setTools([]);
      setSeries(null);
      setComposition(null);
      setRoi([]);
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
      api.composition(window),
      api.roi({ since: filter.since, until: filter.until }),
    ])
      .then(([topicRows, toolRows, ts, comp, roiRows]) => {
        if (!active) return;
        setTopics(topicRows);
        setTools(toolRows);
        setSeries(ts);
        setComposition(comp);
        setRoi(roiRows);
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [filter, granularity, reloadKey, t]);

  // Budget is always "this day/week/month" — independent of the date filter.
  useEffect(() => {
    let active = true;
    api
      .budget()
      .then((b) => active && setBudget(b))
      .catch(() => active && setBudget(null));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const chartData = series ? totalsChartData(series) : [];
  const activeSeconds = roi.reduce((s, r) => s + r.active_seconds, 0);

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
          <StatsCards
            rows={topics}
            extraLabel={t("dimension.topic")}
            activeSeconds={activeSeconds}
          />
          {budget && <BudgetPanel status={budget} />}
          {composition && (
            <CompositionCard
              data={composition}
              onSeeActivity={onNavigate ? () => onNavigate("activity") : undefined}
            />
          )}
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

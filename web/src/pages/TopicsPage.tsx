import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type Dimension, type Rollup } from "../lib/api";
import type { DateFilter } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { StatsCards } from "../components/StatsCards";
import { RollupChart } from "../components/RollupChart";
import { RollupTable } from "../components/RollupTable";

interface Props {
  filter: DateFilter;
  onDrillTopic: (topic: string) => void;
  reloadKey?: number;
}

const DIMENSIONS: Dimension[] = ["topic", "project", "tool", "model"];

export function TopicsPage({ filter, onDrillTopic, reloadKey }: Props) {
  const { t } = useTranslation();
  const [dimension, setDimension] = useState<Dimension>("topic");
  const [rows, setRows] = useState<Rollup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const drillable = dimension === "topic";
  const dimLabel = t(`dimension.${dimension}`);

  useEffect(() => {
    if (rangeInvalid(filter)) {
      setLoading(false);
      setRows([]);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    api
      .report(dimension, { since: filter.since, until: filter.until })
      .then((data) => active && setRows(data))
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [dimension, filter, reloadKey, t]);

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.topics")}</h2>
        <p className="muted">{t("pages.topicsHint")}</p>
      </header>

      <div className="control-group page-controls">
        <span className="control-label">{t("controls.groupBy")}</span>
        {DIMENSIONS.map((d) => (
          <button
            key={d}
            type="button"
            className={d === dimension ? "chip active" : "chip"}
            onClick={() => setDimension(d)}
          >
            {t(`dimension.${d}`)}
          </button>
        ))}
      </div>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : rows.length === 0 ? (
        <p className="muted">{t("app.noData")}</p>
      ) : (
        <>
          <StatsCards rows={rows} extraLabel={t("dimension.count", { name: dimLabel })} />
          <RollupChart rows={rows} dimension={dimension} />
          <RollupTable
            rows={rows}
            dimension={dimension}
            onDrill={drillable ? onDrillTopic : undefined}
            showVsAverage={drillable}
          />
          {drillable && (
            <p className="muted small hint-line">{t("app.drillTip")}</p>
          )}
        </>
      )}
    </div>
  );
}

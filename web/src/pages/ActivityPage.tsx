import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { api, type ActivityCount, type ActivityReport } from "../lib/api";
import type { DateFilter } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { fmtTokens } from "../lib/format";
import { ToolIcon } from "../components/ToolIcon";

interface Props {
  filter: DateFilter;
  reloadKey?: number;
}

// A horizontal bar list. Each row shows two figures: how often the tool/MCP was
// called, and the estimated tokens it returned into the context. The bar is
// scaled to call count. The token figure is "—" when not recorded (e.g. Copilot
// tools, whose results aren't logged).
function BarList({
  rows,
  icon,
  unit,
  tokenLabel,
}: {
  rows: ActivityCount[];
  icon?: (label: string) => ReactNode;
  unit: string;
  tokenLabel: string;
}) {
  const max = rows.reduce((m, r) => Math.max(m, r.count), 0) || 1;
  const anyTokens = rows.some((r) => r.result_tokens > 0);
  return (
    <ul className="activity-bars">
      {rows.map((r) => (
        <li key={r.label} className="activity-bar-row">
          <span className="activity-bar-label" title={r.label}>
            {icon?.(r.label)}
            <span className="activity-bar-text">{r.label}</span>
          </span>
          <span className="activity-bar-track">
            <span
              className="activity-bar-fill"
              style={{ width: `${(100 * r.count) / max}%` }}
            />
          </span>
          <span className="activity-bar-count">
            {r.count.toLocaleString()}
            <span className="muted"> {unit}</span>
          </span>
          {anyTokens && (
            <span className="activity-bar-tokens" title={tokenLabel}>
              {r.result_tokens > 0 ? (
                <>
                  ~{fmtTokens(r.result_tokens)}
                  <span className="muted"> tok</span>
                </>
              ) : (
                <span className="muted">—</span>
              )}
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

// File paths are long; show the basename prominently and the dir muted.
function fileLabel(path: string) {
  const idx = path.lastIndexOf("/");
  if (idx === -1) return <span className="activity-bar-text">{path}</span>;
  return (
    <span className="activity-bar-text">
      <span className="muted">{path.slice(0, idx + 1)}</span>
      {path.slice(idx + 1)}
    </span>
  );
}

export function ActivityPage({ filter, reloadKey }: Props) {
  const { t } = useTranslation();
  const [data, setData] = useState<ActivityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (rangeInvalid(filter)) {
      setLoading(false);
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    api
      .activity({ since: filter.since, until: filter.until })
      .then((d) => active && setData(d))
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [filter, reloadKey, t]);

  const unit = t("activity.times");

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.activity")}</h2>
        <p className="muted">{t("pages.activityHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : !data || data.total_actions === 0 ? (
        <p className="muted">{t("activity.empty")}</p>
      ) : (
        <>
          <section className="stats">
            <div className="stat">
              <div className="stat-label">{t("activity.totalActions")}</div>
              <div className="stat-value">{data.total_actions.toLocaleString()}</div>
            </div>
          </section>

          <section className="card">
            <h2>{t("activity.byTool")}</h2>
            <p className="muted activity-note">{t("activity.tokenNote")}</p>
            {/* Built-in tools (Bash, Read…) have no per-tool icon; the plain
                list reads cleaner than forcing a generic glyph on each row. */}
            <BarList rows={data.by_tool} unit={unit} tokenLabel={t("activity.returnTokens")} />
          </section>

          <section className="card">
            <h2>{t("activity.byMcp")}</h2>
            {data.by_mcp.length === 0 ? (
              <p className="muted">{t("activity.noMcp")}</p>
            ) : (
              <BarList
                rows={data.by_mcp}
                unit={unit}
                tokenLabel={t("activity.returnTokens")}
                icon={(label) => <ToolIcon tool={label} size={16} />}
              />
            )}
          </section>

          <section className="card">
            <h2>{t("activity.topFiles")}</h2>
            {data.top_files.length === 0 ? (
              <p className="muted">{t("activity.noFiles")}</p>
            ) : (
              <ul className="activity-bars">
                {data.top_files.map((r) => {
                  const max = data.top_files[0]?.count || 1;
                  return (
                    <li key={r.label} className="activity-bar-row">
                      <span className="activity-bar-label" title={r.label}>
                        {fileLabel(r.label)}
                      </span>
                      <span className="activity-bar-track">
                        <span
                          className="activity-bar-fill"
                          style={{ width: `${(100 * r.count) / max}%` }}
                        />
                      </span>
                      <span className="activity-bar-count">
                        {r.count.toLocaleString()}
                        <span className="muted"> {unit}</span>
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}

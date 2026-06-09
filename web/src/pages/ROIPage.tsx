import { useTranslation } from "react-i18next";
import { api, type TopicROI } from "../lib/api";
import type { DateFilter } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { useFetch } from "../hooks/useFetch";
import { fmtTokens, fmtUsd, fmtDuration } from "../lib/format";

interface Props {
  filter: DateFilter;
  reloadKey?: number;
}

export function ROIPage({ filter, reloadKey }: Props) {
  const { t } = useTranslation();
  const invalid = rangeInvalid(filter);
  const { data, loading, error } = useFetch<TopicROI[]>(
    () => (invalid ? Promise.resolve([]) : api.roi({ since: filter.since, until: filter.until })),
    [filter.since, filter.until, reloadKey, invalid],
  );

  const rows = data ?? [];
  // Highest burn rate gets flagged — the "spending fast" signal.
  const rates = rows.map((r) => r.usd_per_hour).filter((r): r is number => r != null);
  const hottest = rates.length ? Math.max(...rates) : null;

  const totalCost = rows.reduce((s, r) => s + r.cost_usd, 0);
  const totalMin = rows.reduce((s, r) => s + r.active_minutes, 0);
  const blendedRate = totalMin > 0 ? totalCost / (totalMin / 60) : null;

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.roi")}</h2>
        <p className="muted">{t("pages.roiHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : rows.length === 0 ? (
        <p className="muted">{t("app.noData")}</p>
      ) : (
        <>
          <section className="stats">
            <div className="stat">
              <div className="stat-label">{t("roi.totalCost")}</div>
              <div className="stat-value">{fmtUsd(totalCost)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("roi.totalActive")}</div>
              <div className="stat-value">{fmtDuration(totalMin)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("roi.blendedRate")}</div>
              <div className="stat-value">
                {blendedRate != null ? `${fmtUsd(blendedRate)}/h` : t("common.dash")}
              </div>
            </div>
          </section>

          <section className="card">
            <table>
              <thead>
                <tr>
                  <th>{t("dimension.topic")}</th>
                  <th className="num">{t("roi.sessions")}</th>
                  <th className="num">{t("session.calls")}</th>
                  <th className="num">{t("table.tokens")}</th>
                  <th className="num">{t("roi.active")}</th>
                  <th className="num">{t("table.cost")}</th>
                  <th className="num">{t("roi.perHour")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const flagged = hottest != null && r.usd_per_hour === hottest;
                  return (
                    <tr key={r.topic}>
                      <td>
                        {r.topic}
                        {r.estimated && (
                          <span className="badge est small-badge">{t("common.estimated")}</span>
                        )}
                      </td>
                      <td className="num">{r.sessions}</td>
                      <td className="num">{r.interactions}</td>
                      <td className="num">{fmtTokens(r.total_tokens)}</td>
                      <td className="num">{fmtDuration(r.active_minutes)}</td>
                      <td className="num cost">{fmtUsd(r.cost_usd)}</td>
                      <td className={flagged ? "num rate-hot" : "num"}>
                        {r.usd_per_hour != null ? `${fmtUsd(r.usd_per_hour)}/h` : t("common.dash")}
                        {flagged && <span className="rate-flag" title={t("roi.flagHint")}>🔥</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="muted small hint-line">{t("roi.methodHint")}</p>
          </section>
        </>
      )}
    </div>
  );
}

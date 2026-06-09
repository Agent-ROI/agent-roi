import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type TopicROI } from "../lib/api";
import type { DateFilter } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { useFetch } from "../hooks/useFetch";
import { fmtTokens, fmtUsd, fmtDuration } from "../lib/format";
import { Pagination } from "../components/Pagination";

const PAGE_SIZE = 12;

interface Props {
  filter: DateFilter;
  reloadKey?: number;
}

// Turn the unitless coefficient of variation into a human label. The cut points
// are the usual rule-of-thumb bands for CV, not tuned to any one user's data:
// < 0.5 tight, < 1.0 moderate spread, >= 1.0 the stdev exceeds the mean.
function consistencyOf(cv: number | null): "stable" | "moderate" | "volatile" | null {
  if (cv == null) return null;
  if (cv < 0.5) return "stable";
  if (cv < 1.0) return "moderate";
  return "volatile";
}

export function ROIPage({ filter, reloadKey }: Props) {
  const { t } = useTranslation();
  const invalid = rangeInvalid(filter);
  const { data, loading, error } = useFetch<TopicROI[]>(
    () => (invalid ? Promise.resolve([]) : api.roi({ since: filter.since, until: filter.until })),
    [filter.since, filter.until, reloadKey, invalid],
  );
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  // Lead with unit economics: most expensive *per piece of work* first.
  const sorted = useMemo(
    () => [...(data ?? [])].sort((a, b) => b.cost_per_session - a.cost_per_session),
    [data],
  );

  // Headline averages span the whole window, independent of the search filter.
  const totalSessions = sorted.reduce((s, r) => s + r.sessions, 0);
  const totalCost = sorted.reduce((s, r) => s + r.cost_usd, 0);
  const totalMin = sorted.reduce((s, r) => s + r.active_minutes, 0);
  const avgCost = totalSessions > 0 ? totalCost / totalSessions : null;
  const avgMin = totalSessions > 0 ? totalMin / totalSessions : null;

  const filtered = useMemo(
    () =>
      search.trim()
        ? sorted.filter((r) => r.topic.toLowerCase().includes(search.trim().toLowerCase()))
        : sorted,
    [sorted, search],
  );
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const safePage = Math.min(page, Math.max(0, totalPages - 1));
  const rows = filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.roi")}</h2>
        <p className="muted">{t("pages.roiHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : sorted.length === 0 ? (
        <p className="muted">{t("app.noData")}</p>
      ) : (
        <>
          <section className="stats">
            <div className="stat">
              <div className="stat-label">{t("roi.avgCost")}</div>
              <div className="stat-value">{avgCost != null ? fmtUsd(avgCost) : t("common.dash")}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("roi.avgTime")}</div>
              <div className="stat-value">{avgMin != null ? fmtDuration(avgMin) : t("common.dash")}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("roi.totalActive")}</div>
              <div className="stat-value">{fmtDuration(totalMin)}</div>
            </div>
          </section>

          <section className="card">
            <h3>{t("roi.perSessionTitle")}</h3>
            <input
              type="text"
              className="session-search"
              placeholder={t("roi.searchTopics")}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
            {rows.length === 0 ? (
              <p className="muted">{t("app.noData")}</p>
            ) : (
            <table>
              <thead>
                <tr>
                  <th>{t("dimension.topic")}</th>
                  <th className="num">{t("roi.sessions")}</th>
                  <th className="num">{t("roi.costPerSession")}</th>
                  <th className="num">{t("roi.timePerSession")}</th>
                  <th className="num">{t("roi.tokensPerSession")}</th>
                  <th className="num">{t("roi.consistency")}</th>
                  <th className="num">{t("roi.perHour")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const c = consistencyOf(r.cost_cv);
                  return (
                    <tr key={r.topic}>
                      <td>
                        {r.topic}
                        {r.estimated && (
                          <span className="badge est small-badge">{t("common.estimated")}</span>
                        )}
                      </td>
                      <td className="num">{r.sessions}</td>
                      <td className="num cost">{fmtUsd(r.cost_per_session)}</td>
                      <td className="num">{fmtDuration(r.minutes_per_session)}</td>
                      <td className="num">{fmtTokens(r.tokens_per_session)}</td>
                      <td className="num">
                        {c ? (
                          <span
                            className={c === "volatile" ? "rate-hot" : "muted"}
                            title={t("roi.consistencyHint")}
                          >
                            {t(`roi.${c}`)}
                          </span>
                        ) : (
                          t("common.dash")
                        )}
                      </td>
                      <td className="num">
                        {r.usd_per_hour != null ? `${fmtUsd(r.usd_per_hour)}/h` : t("common.dash")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            )}
            {totalPages > 1 && (
              <Pagination page={safePage} totalPages={totalPages} onChange={setPage} />
            )}
            <p className="muted small hint-line">{t("roi.methodHint")}</p>
          </section>
        </>
      )}
    </div>
  );
}

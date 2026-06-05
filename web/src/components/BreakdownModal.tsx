import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  api,
  type TopicBreakdown,
  type Rollup,
  type SessionSummary,
} from "../lib/api";
import type { DateFilter } from "../lib/dateFilter";
import { rangeInvalid } from "../lib/dateFilter";
import { fmtTokens, fmtUsd } from "../lib/format";
import { SessionModal } from "./SessionModal";

interface Props {
  topic: string;
  filter: DateFilter;
  onClose: () => void;
}

export function BreakdownModal({ topic, filter, onClose }: Props) {
  const { t } = useTranslation();
  const [data, setData] = useState<TopicBreakdown | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [openSession, setOpenSession] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (rangeInvalid(filter)) return;
    let active = true;
    const window = { since: filter.since, until: filter.until };
    Promise.all([api.topic(topic, window), api.sessions(topic, window)])
      .then(([d, s]) => {
        if (!active) return;
        setData(d);
        setSessions(s);
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")));
    return () => {
      active = false;
    };
  }, [topic, filter, t]);

  return (
    <>
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>{topic}</h2>
            <button className="chip" onClick={onClose}>
              ✕
            </button>
          </div>

          {error && <div className="error">⚠ {error}</div>}
          {!data ? (
            <p className="muted">{t("common.loading")}</p>
          ) : (
            <>
              <p className="muted">
                {t("breakdown.summary", {
                  interactions: data.total.interactions,
                  sessions: sessions.length,
                  tokens: fmtTokens(data.total.total_tokens),
                  cost: fmtUsd(data.total.cost_usd),
                })}
                {data.total.estimated && (
                  <span className="badge est"> {t("breakdown.includesEstimates")}</span>
                )}
              </p>
              <SplitTable
                title={t("breakdown.byTool")}
                colKey={t("breakdown.tool")}
                rows={data.by_tool}
                total={data.total.cost_usd}
              />
              <SplitTable
                title={t("breakdown.byModel")}
                colKey={t("breakdown.model")}
                rows={data.by_model}
                total={data.total.cost_usd}
              />
              <SessionsTable sessions={sessions} onOpen={setOpenSession} />
            </>
          )}
        </div>
      </div>

      {openSession && (
        <SessionModal sessionId={openSession} onClose={() => setOpenSession(null)} />
      )}
    </>
  );
}

function SessionsTable({
  sessions,
  onOpen,
}: {
  sessions: SessionSummary[];
  onOpen: (id: string) => void;
}) {
  const { t } = useTranslation();
  if (!sessions.length) return null;
  return (
    <section className="card">
      <h3>{t("breakdown.sessions", { count: sessions.length })}</h3>
      <p className="muted small">{t("breakdown.sessionsHint")}</p>
      <table>
        <thead>
          <tr>
            <th>{t("table.project")}</th>
            <th>{t("table.tools")}</th>
            <th className="num">{t("table.calls")}</th>
            <th className="num">{t("table.tokens")}</th>
            <th className="num">{t("table.cost")}</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr
              key={s.session_id}
              className="drillable"
              onClick={(e) => {
                e.stopPropagation();
                onOpen(s.session_id);
              }}
              title={t("table.openSession")}
            >
              <td>
                {s.project || <span className="muted">{t("common.unknown")}</span>}
                <span className="drill-hint"> ›</span>
              </td>
              <td>{s.tools.join(", ")}</td>
              <td className="num">{s.interactions}</td>
              <td className="num">{fmtTokens(s.total_tokens)}</td>
              <td className="num cost">{fmtUsd(s.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function SplitTable({
  title,
  colKey,
  rows,
  total,
}: {
  title: string;
  colKey: string;
  rows: Rollup[];
  total: number;
}) {
  const { t } = useTranslation();
  return (
    <section className="card">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>{colKey}</th>
            <th className="num">{t("table.tokens")}</th>
            <th className="num">{t("table.cost")}</th>
            <th className="num">{t("table.share")}</th>
            <th>{t("table.source")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.key}</td>
              <td className="num">{fmtTokens(r.total_tokens)}</td>
              <td className="num cost">{fmtUsd(r.cost_usd)}</td>
              <td className="num">
                {total ? `${Math.round((r.cost_usd / total) * 100)}%` : t("common.dash")}
              </td>
              <td>
                <span className={r.estimated ? "badge est" : "badge exact"}>
                  {r.estimated ? t("common.estimated") : t("common.exact")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

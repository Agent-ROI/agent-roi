import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type SessionDetail } from "../lib/api";
import { fmtTokens, fmtUsd, fmtDateTime, fmtTimeRange, fmtDuration } from "../lib/format";
import { classificationSnippets, groupCalls, type CallGroup } from "../lib/sessionView";
import { Pagination } from "./Pagination";

interface Props {
  sessionId: string;
  onClose: () => void;
}

export function SessionModal({ sessionId, onClose }: Props) {
  const { t } = useTranslation();
  const [data, setData] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [groupsPage, setGroupsPage] = useState(0);

  useEffect(() => {
    let active = true;
    api
      .session(sessionId)
      .then((d) => active && setData(d))
      .catch((e) => active && setError(e instanceof Error ? e.message : t("common.failed")));
    return () => {
      active = false;
    };
  }, [sessionId, t]);

  const s = data?.session;
  const groups = useMemo(
    () => (data ? groupCalls(data.interactions) : []),
    [data]
  );
  const snippets = useMemo(
    () => (data ? classificationSnippets(data.interactions) : []),
    [data]
  );

  return (
    <div className="modal-backdrop session" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{t("session.title")}</h2>
          <button className="chip" onClick={onClose}>
            ✕
          </button>
        </div>

        {error && <div className="error">⚠ {error}</div>}
        {!s ? (
          <p className="muted">{t("common.loading")}</p>
        ) : (
          <>
            <div className="callout">
              <p>{t("session.explainer")}</p>
            </div>

            <div className="session-hero">
              <div className="session-hero-topic">{s.topic}</div>
              <div className="session-hero-meta muted">
                {s.project && <span>{s.project} · </span>}
                {t("session.meta", {
                  calls: s.interactions,
                  tokens: fmtTokens(s.total_tokens),
                  cost: fmtUsd(s.cost_usd),
                })}
                {s.active_seconds > 0 && (
                  <span>
                    {" · "}
                    {fmtDuration(s.active_minutes)}
                    {s.usd_per_hour != null && ` · ${fmtUsd(s.usd_per_hour)}/h`}
                  </span>
                )}
              </div>
              <div className="pill-row">
                {s.tools.map((tool) => (
                  <span key={tool} className="badge tool">
                    {tool}
                  </span>
                ))}
                {s.models.map((m) => (
                  <span key={m} className="badge model">
                    {m}
                  </span>
                ))}
              </div>
            </div>

            {snippets.length > 0 && (
              <section className="card card-tint">
                <h3>{t("session.classificationTitle")}</h3>
                <p className="muted small">{t("session.classificationHint")}</p>
                <ul className="snippet-list">
                  {snippets.map((text) => (
                    <li key={text}>{text}</li>
                  ))}
                </ul>
              </section>
            )}

            <section className="card">
              <h3>{t("session.groupsTitle", { count: groups.length })}</h3>
              {(() => {
                const PAGE = 15;
                const totalPages = Math.ceil(groups.length / PAGE);
                const visible = groups.slice(groupsPage * PAGE, (groupsPage + 1) * PAGE);
                return (
                  <>
                    <table>
                      <thead>
                        <tr>
                          <th>{t("session.pattern")}</th>
                          <th className="num">{t("session.calls")}</th>
                          <th className="num">{t("table.tokens")}</th>
                          <th className="num">{t("table.cost")}</th>
                          <th>{t("session.timeSpan")}</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {visible.map((g) => (
                          <GroupRows
                            key={g.summary || "__empty__"}
                            group={g}
                            expanded={expandedGroup === (g.summary || "__empty__")}
                            onToggle={() =>
                              setExpandedGroup((cur) =>
                                cur === (g.summary || "__empty__")
                                  ? null
                                  : g.summary || "__empty__"
                              )
                            }
                          />
                        ))}
                      </tbody>
                    </table>
                    {totalPages > 1 && (
                      <Pagination page={groupsPage} totalPages={totalPages} onChange={setGroupsPage} />
                    )}
                  </>
                );
              })()}
            </section>

            <button className="chip raw-toggle" onClick={() => setShowRaw((v) => !v)}>
              {showRaw
                ? t("session.hideIndividual", { count: s.interactions })
                : t("session.showIndividual", { count: s.interactions })}
            </button>

            {showRaw && (
              <section className="card card-muted">
                <h3>{t("session.rawTitle", { count: s.interactions })}</h3>
                <table>
                  <thead>
                    <tr>
                      <th>{t("table.when")}</th>
                      <th>{t("table.toolModel")}</th>
                      <th className="num">{t("table.tokens")}</th>
                      <th className="num">{t("table.cost")}</th>
                      <th>{t("table.snippet")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data!.interactions.map((i) => (
                      <tr key={i.id}>
                        <td className="nowrap">{fmtDateTime(i.timestamp)}</td>
                        <td>
                          {i.tool}
                          <div className="muted small">{i.model}</div>
                        </td>
                        <td className="num">{fmtTokens(i.total_tokens)}</td>
                        <td className="num cost">{fmtUsd(i.cost_usd)}</td>
                        <td className="snippet">
                          {i.summary || t("session.noSnippet")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function GroupRows({
  group,
  expanded,
  onToggle,
}: {
  group: CallGroup;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  const label = group.summary || t("session.noSnippet");
  const canExpand = group.count > 1;

  return (
    <>
      <tr className={canExpand ? "drillable" : undefined} onClick={canExpand ? onToggle : undefined}>
        <td className="pattern-cell">
          <span className="pattern-text">{label}</span>
          {group.estimated && (
            <span className="badge est small-badge">{t("common.estimated")}</span>
          )}
        </td>
        <td className="num">
          <strong>{group.count}</strong>
          {group.count > 1 && <span className="muted small"> {t("session.callsUnit")}</span>}
        </td>
        <td className="num">{fmtTokens(group.totalTokens)}</td>
        <td className="num cost">{fmtUsd(group.costUsd)}</td>
        <td className="nowrap muted small">
          {fmtTimeRange(group.firstAt, group.lastAt)}
        </td>
        <td className="expand-col">
          {canExpand && <span className="drill-hint">{expanded ? "▾" : "▸"}</span>}
        </td>
      </tr>
      {expanded &&
        group.items.map((i) => (
          <tr key={i.id} className="group-detail">
            <td className="indent muted small">{fmtDateTime(i.timestamp)}</td>
            <td className="muted small">{i.tool} / {i.model}</td>
            <td className="num muted small">1</td>
            <td className="num muted small">{fmtTokens(i.total_tokens)}</td>
            <td className="num cost small">{fmtUsd(i.cost_usd)}</td>
            <td />
          </tr>
        ))}
    </>
  );
}

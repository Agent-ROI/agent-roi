import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { api, type Sources } from "../lib/api";
import { fmtUsd } from "../lib/format";
import { ToolIcon, toolDisplayName } from "./ToolIcon";

function translateNote(note: string, t: TFunction): string {
  if (note.includes("No logs found")) return t("sources.noteNotFound");
  if (note.includes("not ingested")) return t("sources.noteNeedsSync");
  return note;
}

export function SourcesPanel({ reloadKey }: { reloadKey: number }) {
  const { t } = useTranslation();
  const [data, setData] = useState<Sources | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .sources()
      .then((d) => active && setData(d))
      .catch(() => active && setData(null));
    return () => {
      active = false;
    };
  }, [reloadKey]);

  if (!data) return null;

  const detected = data.collectors.filter((c) => c.interactions > 0).length;

  return (
    <section className="card">
      <div className="sources-head" onClick={() => setOpen((v) => !v)}>
        <h2>
          {t("sources.title")} <span className="muted">· {data.platform}</span>
        </h2>
        <span className="muted">
          {t("sources.activeCount", { detected, total: data.collectors.length })}{" "}
          {open ? "▾" : "▸"}
        </span>
      </div>

      <table>
        <thead>
          <tr>
            <th>{t("sources.tool")}</th>
            <th>{t("sources.status")}</th>
            <th className="num">{t("sources.logFiles")}</th>
            <th className="num">{t("sources.interactions")}</th>
            <th className="num">{t("sources.cost")}</th>
            {open && <th>{t("sources.searched")}</th>}
          </tr>
        </thead>
        <tbody>
          {data.collectors.map((c) => (
            <tr key={c.name}>
              <td>
                <span className="tool-name-cell">
                  <ToolIcon tool={c.name} size={18} />
                  <span>{toolDisplayName(c.name)}</span>
                </span>
              </td>
              <td>
                {c.interactions > 0 ? (
                  <span className="badge exact">{t("sources.active")}</span>
                ) : c.available ? (
                  <span className="badge est">{t("sources.needsSync")}</span>
                ) : (
                  <span className="badge off">{t("sources.notFound")}</span>
                )}
                {c.note && <div className="source-note">{translateNote(c.note, t)}</div>}
              </td>
              <td className="num">{c.log_files}</td>
              <td className="num">{c.interactions.toLocaleString()}</td>
              <td className="num cost">{fmtUsd(c.cost_usd)}</td>
              {open && (
                <td className="source-paths">
                  {c.search_paths.length ? c.search_paths.join("  ·  ") : t("common.dash")}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

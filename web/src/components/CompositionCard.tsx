import { useTranslation } from "react-i18next";
import type { CompositionBundle, TokenComposition } from "../lib/api";
import { fmtTokens } from "../lib/format";
import { ToolIcon, toolDisplayName } from "./ToolIcon";

const COLORS = {
  overhead: "var(--warning)",
  cached: "var(--accent)",
  work: "var(--success)",
} as const;

interface Props {
  data: CompositionBundle;
  onSeeActivity?: () => void;
}

function Bar({ c }: { c: TokenComposition }) {
  // A zero-width segment would still show a sliver via min-width; guard it.
  const seg = (pct: number, color: string, label: string) =>
    pct > 0 ? (
      <span
        key={label}
        className="composition-seg"
        style={{ width: `${pct}%`, background: color }}
        title={`${label} ${pct}%`}
      />
    ) : null;
  return (
    <div className="composition-bar">
      {seg(c.overhead_pct, COLORS.overhead, "overhead")}
      {seg(c.cached_pct, COLORS.cached, "cached")}
      {seg(c.work_pct, COLORS.work, "work")}
    </div>
  );
}

export function CompositionCard({ data, onSeeActivity }: Props) {
  const { t } = useTranslation();
  const { total, by_tool } = data;

  const legend: Array<{ key: keyof typeof COLORS; tokens: number; pct: number; hint: string }> = [
    {
      key: "overhead",
      tokens: total.overhead,
      pct: total.overhead_pct,
      hint: t("composition.overheadHint"),
    },
    { key: "cached", tokens: total.cached, pct: total.cached_pct, hint: t("composition.cachedHint") },
    { key: "work", tokens: total.work, pct: total.work_pct, hint: t("composition.workHint") },
  ];

  return (
    <section className="card composition-card">
      <header className="composition-head">
        <h2>{t("composition.title")}</h2>
        <p className="muted">{t("composition.hint")}</p>
      </header>

      <Bar c={total} />

      <div className="composition-legend">
        {legend.map((l) => (
          <div className="composition-legend-item" key={l.key} title={l.hint}>
            <span className="composition-swatch" style={{ background: COLORS[l.key] }} />
            <div>
              <div className="composition-legend-label">{t(`composition.${l.key}`)}</div>
              <div className="composition-legend-value">
                {fmtTokens(l.tokens)}
                {total.estimated && (
                  <span className="est-badge" title={t("composition.estimatedNote")}>
                    ~
                  </span>
                )}{" "}
                <span className="muted">· {l.pct}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {by_tool.length > 0 && (
        <div className="composition-tools">
          <h3 className="composition-subtitle">{t("composition.byTool")}</h3>
          {by_tool.map((c) => (
            <div className="composition-tool-row" key={c.tool}>
              <span className="composition-tool-name">
                <ToolIcon tool={c.tool} size={16} />
                {toolDisplayName(c.tool)}
                {c.estimated && (
                  <span className="est-badge" title={t("composition.estimatedNote")}>
                    ~
                  </span>
                )}
              </span>
              <Bar c={c} />
            </div>
          ))}
        </div>
      )}

      {onSeeActivity && (
        <button type="button" className="composition-link" onClick={onSeeActivity}>
          {t("composition.seeActivity")} →
        </button>
      )}
    </section>
  );
}

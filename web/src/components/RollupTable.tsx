import { useTranslation } from "react-i18next";
import type { Rollup, Dimension } from "../lib/api";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  rows: Rollup[];
  dimension: Dimension;
  onDrill?: (key: string) => void;
  title?: string;
  // Show each row's cost relative to the average across rows — the "is this
  // topic above or below my typical spend?" ROI signal.
  showVsAverage?: boolean;
}

export function RollupTable({ rows, dimension, onDrill, title, showVsAverage }: Props) {
  const { t } = useTranslation();
  const sorted = rows.slice().sort((a, b) => b.cost_usd - a.cost_usd);
  const drillable = dimension === "topic" && !!onDrill;
  const dimLabel = t(`dimension.${dimension}`);
  const avgCost =
    sorted.length > 0 ? sorted.reduce((sum, r) => sum + r.cost_usd, 0) / sorted.length : 0;

  return (
    <section className="card">
      <h2>{title ?? t("dimension.all", { name: dimLabel })}</h2>
      <table>
        <thead>
          <tr>
            <th>{dimLabel}</th>
            <th className="num">{t("table.interactions")}</th>
            <th className="num">{t("table.input")}</th>
            <th className="num">{t("table.output")}</th>
            <th className="num">{t("table.totalTokens")}</th>
            <th className="num">{t("table.cost")}</th>
            {showVsAverage && <th className="num">{t("table.vsAverage")}</th>}
            <th>{t("table.source")}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const ratio = avgCost > 0 ? r.cost_usd / avgCost : 0;
            const tone = ratio >= 1.25 ? "above" : ratio <= 0.75 ? "below" : "near";
            return (
            <tr
              key={r.key}
              className={drillable ? "drillable" : undefined}
              onClick={drillable ? () => onDrill!(r.key) : undefined}
              title={drillable ? t("table.drillBreakdown") : undefined}
            >
              <td>
                {r.key}
                {drillable && <span className="drill-hint"> ›</span>}
              </td>
              <td className="num">{r.interactions}</td>
              <td className="num">{fmtTokens(r.input_tokens)}</td>
              <td className="num">{fmtTokens(r.output_tokens)}</td>
              <td className="num">{fmtTokens(r.total_tokens)}</td>
              <td className="num cost">{fmtUsd(r.cost_usd)}</td>
              {showVsAverage && (
                <td className="num">
                  <span className={`vs-avg ${tone}`}>
                    {ratio > 0 ? `${ratio.toFixed(1)}×` : "—"}
                  </span>
                </td>
              )}
              <td>
                <span className={r.estimated ? "badge est" : "badge exact"}>
                  {r.estimated ? t("common.estimated") : t("common.exact")}
                </span>
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

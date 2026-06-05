import { useTranslation } from "react-i18next";
import type { Rollup } from "../lib/api";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  rows: Rollup[];
  extraLabel?: string;
}

export function StatsCards({ rows, extraLabel }: Props) {
  const { t } = useTranslation();
  const totalCost = rows.reduce((sum, r) => sum + r.cost_usd, 0);
  const totalTokens = rows.reduce((sum, r) => sum + r.total_tokens, 0);
  const totalInteractions = rows.reduce((sum, r) => sum + r.interactions, 0);
  const anyEstimated = rows.some((r) => r.estimated);

  return (
    <section className="stats">
      <div className="stat">
        <div className="stat-label">{t("stats.totalCost")}</div>
        <div className="stat-value">{fmtUsd(totalCost)}</div>
        {anyEstimated && (
          <div className="stat-foot est">{t("stats.includesEstimates")}</div>
        )}
      </div>
      <div className="stat">
        <div className="stat-label">{t("stats.totalTokens")}</div>
        <div className="stat-value">{fmtTokens(totalTokens)}</div>
      </div>
      <div className="stat">
        <div className="stat-label">{t("stats.interactions")}</div>
        <div className="stat-value">{fmtTokens(totalInteractions)}</div>
      </div>
      {extraLabel && (
        <div className="stat">
          <div className="stat-label">{extraLabel}</div>
          <div className="stat-value">{rows.length}</div>
        </div>
      )}
    </section>
  );
}

import { useTranslation } from "react-i18next";
import type { Rollup } from "../lib/api";
import { fmtTokens, fmtUsd, fmtDuration } from "../lib/format";
import { useCountUp } from "../lib/useCountUp";

interface Props {
  rows: Rollup[];
  extraLabel?: string;
  // Active development time (idle excluded) across the window, in seconds.
  // When provided, two extra cards surface "how long" and "$/hour".
  activeSeconds?: number;
}

export function StatsCards({ rows, extraLabel, activeSeconds }: Props) {
  const { t } = useTranslation();
  const totalCost = rows.reduce((sum, r) => sum + r.cost_usd, 0);
  const totalTokens = rows.reduce((sum, r) => sum + r.total_tokens, 0);
  const totalInteractions = rows.reduce((sum, r) => sum + r.interactions, 0);
  const anyEstimated = rows.some((r) => r.estimated);

  const hasTime = activeSeconds != null && activeSeconds > 0;
  const blendedRate = hasTime ? totalCost / (activeSeconds! / 3600) : null;

  // Count-up the numeric stats (time stays as-is — duration formatting can't lerp).
  const costAnim = useCountUp(totalCost);
  const tokensAnim = useCountUp(totalTokens);
  const interactionsAnim = useCountUp(totalInteractions);

  return (
    <section className="stats">
      <div className="stat">
        <div className="stat-label">{t("stats.totalCost")}</div>
        <div className="stat-value">{fmtUsd(costAnim)}</div>
        {anyEstimated && (
          <div className="stat-foot est">{t("stats.includesEstimates")}</div>
        )}
      </div>
      {hasTime && (
        <div className="stat">
          <div className="stat-label">{t("roi.totalActive")}</div>
          <div className="stat-value">{fmtDuration(activeSeconds! / 60)}</div>
          <div className="stat-foot">
            {blendedRate != null ? `${fmtUsd(blendedRate)}/h` : ""}
          </div>
        </div>
      )}
      <div className="stat">
        <div className="stat-label">{t("stats.totalTokens")}</div>
        <div className="stat-value">{fmtTokens(tokensAnim)}</div>
      </div>
      <div className="stat">
        <div className="stat-label">{t("stats.interactions")}</div>
        <div className="stat-value">{fmtTokens(interactionsAnim)}</div>
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

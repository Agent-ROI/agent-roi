import { useTranslation } from "react-i18next";
import type { BudgetStatus } from "../lib/api";
import { fmtUsd } from "../lib/format";

interface Props {
  status: BudgetStatus;
}

/**
 * Day / week / month spend against the configured limits. Periods without a
 * limit still show spend (so the value is visible before a budget is chosen);
 * periods with a limit get a progress bar that turns red when over budget.
 */
export function BudgetPanel({ status }: Props) {
  const { t } = useTranslation();
  const hasAnyLimit = status.periods.some((p) => p.limit_usd !== null);

  return (
    <section className="budget-panel">
      <div className="budget-panel-head">
        <h3>{t("budget.title")}</h3>
        {status.any_over && <span className="budget-alert">⚠ {t("budget.overAlert")}</span>}
      </div>

      {!hasAnyLimit && <p className="muted budget-empty">{t("budget.noneSet")}</p>}

      <div className="budget-grid">
        {status.periods.map((p) => {
          const pct = p.pct ?? 0;
          const clamped = Math.min(pct, 100);
          return (
            <div key={p.period} className={`budget-card${p.over ? " over" : ""}`}>
              <div className="budget-card-head">
                <span className="budget-period">{t(`budget.period.${p.period}`)}</span>
                {p.limit_usd !== null && (
                  <span className={`budget-pct${p.over ? " over" : ""}`}>{Math.round(pct)}%</span>
                )}
              </div>
              <div className="budget-spent">{fmtUsd(p.spent_usd)}</div>
              {p.limit_usd !== null ? (
                <>
                  <div className="budget-bar">
                    <div
                      className={`budget-bar-fill${p.over ? " over" : ""}`}
                      style={{ width: `${clamped}%` }}
                    />
                  </div>
                  <div className="budget-meta muted">
                    {t("budget.ofLimit", { limit: fmtUsd(p.limit_usd) })}
                    {p.remaining_usd !== null && (
                      <span className={p.over ? "budget-over-text" : ""}>
                        {" · "}
                        {p.remaining_usd >= 0
                          ? t("budget.remaining", { amount: fmtUsd(p.remaining_usd) })
                          : t("budget.overBy", { amount: fmtUsd(-p.remaining_usd) })}
                      </span>
                    )}
                  </div>
                </>
              ) : (
                <div className="budget-meta muted">{t("budget.noLimit")}</div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

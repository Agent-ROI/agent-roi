import { useTranslation } from "react-i18next";
import type { DateFilter } from "../../lib/dateFilter";
import { ISO_DATE, isCustomRange } from "../../lib/dateFilter";

interface Props {
  filter: DateFilter;
  onFilter: (filter: DateFilter) => void;
  compact?: boolean;
}

const PRESETS = [
  { key: "allTime", since: "", until: "" },
  { key: "hours24", since: "24h", until: "" },
  { key: "today", since: "today", until: "" },
  { key: "days7", since: "7d", until: "" },
  { key: "days30", since: "30d", until: "" },
  { key: "days90", since: "90d", until: "" },
] as const;

function presetActive(filter: DateFilter, since: string, until: string): boolean {
  return filter.since === since && filter.until === until;
}

export function DateRangeFilter({ filter, onFilter, compact }: Props) {
  const { t } = useTranslation();
  const custom = isCustomRange(filter);
  const fromValue = ISO_DATE.test(filter.since) ? filter.since : "";
  const toValue = ISO_DATE.test(filter.until) ? filter.until : "";
  const invalid = fromValue && toValue && fromValue > toValue;

  return (
    <div className={`date-range-filter${compact ? " compact" : ""}`}>
      <span className="filter-title">{t("controls.range")}</span>
      <div className="range-chips">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            className={
              !custom && presetActive(filter, p.since, p.until) ? "chip active" : "chip"
            }
            onClick={() => onFilter({ since: p.since, until: p.until })}
          >
            {t(`controls.${p.key}`)}
          </button>
        ))}
      </div>
      <div className="date-range-inputs">
        <label className="date-filter">
          <span className="control-label">{t("controls.fromDate")}</span>
          <input
            className="date-input"
            type="date"
            value={fromValue}
            onChange={(e) =>
              onFilter({ since: e.target.value, until: filter.until })
            }
            aria-label={t("controls.fromDate")}
          />
        </label>
        <label className="date-filter">
          <span className="control-label">{t("controls.toDate")}</span>
          <input
            className="date-input"
            type="date"
            value={toValue}
            onChange={(e) =>
              onFilter({ since: filter.since, until: e.target.value })
            }
            aria-label={t("controls.toDate")}
          />
        </label>
      </div>
      {invalid && (
        <p className="range-error">{t("controls.rangeInvalid")}</p>
      )}
    </div>
  );
}

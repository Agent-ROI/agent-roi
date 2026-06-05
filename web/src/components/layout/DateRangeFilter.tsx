import { useTranslation } from "react-i18next";

interface Props {
  since: string;
  onSince: (value: string) => void;
  compact?: boolean;
}

const RANGES = [
  { key: "allTime", value: "" },
  { key: "hours24", value: "24h" },
  { key: "today", value: "today" },
  { key: "days7", value: "7d" },
  { key: "days30", value: "30d" },
  { key: "days90", value: "90d" },
] as const;

export function DateRangeFilter({ since, onSince, compact }: Props) {
  const { t } = useTranslation();
  const isCustomDate = /^\d{4}-\d{2}-\d{2}$/.test(since);

  return (
    <div className={`date-range-filter${compact ? " compact" : ""}`}>
      <span className="filter-title">{t("controls.range")}</span>
      <div className="range-chips">
        {RANGES.map((r) => (
          <button
            key={r.value || "all"}
            type="button"
            className={r.value === since ? "chip active" : "chip"}
            onClick={() => onSince(r.value)}
          >
            {t(`controls.${r.key}`)}
          </button>
        ))}
      </div>
      <label className="date-filter">
        <span className="control-label">{t("controls.fromDate")}</span>
        <input
          className="date-input"
          type="date"
          value={isCustomDate ? since : ""}
          onChange={(e) => onSince(e.target.value)}
          aria-label={t("controls.fromDate")}
        />
      </label>
    </div>
  );
}

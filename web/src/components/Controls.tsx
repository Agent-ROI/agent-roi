import { useTranslation } from "react-i18next";
import type { Dimension } from "../lib/api";

interface Props {
  dimension: Dimension;
  onDimension: (d: Dimension) => void;
  since: string;
  onSince: (s: string) => void;
}

const DIMENSIONS: Dimension[] = ["topic", "project", "tool", "model"];
const RANGES = [
  { key: "allTime", value: "" },
  { key: "hours24", value: "24h" },
  { key: "today", value: "today" },
  { key: "days7", value: "7d" },
  { key: "days30", value: "30d" },
  { key: "days90", value: "90d" },
] as const;

export function Controls({ dimension, onDimension, since, onSince }: Props) {
  const { t } = useTranslation();
  const isCustomDate = /^\d{4}-\d{2}-\d{2}$/.test(since);
  const customDateValue = isCustomDate ? since : "";

  return (
    <div className="controls">
      <div className="control-group">
        <span className="control-label">{t("controls.groupBy")}</span>
        {DIMENSIONS.map((d) => (
          <button
            key={d}
            className={d === dimension ? "chip active" : "chip"}
            onClick={() => onDimension(d)}
          >
            {t(`dimension.${d}`)}
          </button>
        ))}
      </div>
      <div className="control-group">
        <span className="control-label">{t("controls.range")}</span>
        {RANGES.map((r) => (
          <button
            key={r.value}
            className={r.value === since ? "chip active" : "chip"}
            onClick={() => onSince(r.value)}
          >
            {t(`controls.${r.key}`, { defaultValue: r.value || "All time" })}
          </button>
        ))}
        <label className="date-filter">
          <span className="control-label">{t("controls.fromDate", { defaultValue: "From" })}</span>
          <input
            className="date-input"
            type="date"
            value={customDateValue}
            onChange={(e) => onSince(e.target.value)}
            aria-label={t("controls.fromDate", { defaultValue: "From date" })}
          />
        </label>
      </div>
    </div>
  );
}

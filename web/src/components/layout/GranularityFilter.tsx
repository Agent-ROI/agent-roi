import { useTranslation } from "react-i18next";
import type { Granularity } from "../../lib/dateFilter";

interface Props {
  value: Granularity;
  onChange: (value: Granularity) => void;
}

const OPTIONS: Granularity[] = ["day", "week", "month"];

export function GranularityFilter({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <div className="granularity-filter">
      <span className="filter-title">{t("controls.granularity")}</span>
      <div className="range-chips">
        {OPTIONS.map((g) => (
          <button
            key={g}
            type="button"
            className={value === g ? "chip active" : "chip"}
            onClick={() => onChange(g)}
          >
            {t(`controls.granularity_${g}`)}
          </button>
        ))}
      </div>
    </div>
  );
}

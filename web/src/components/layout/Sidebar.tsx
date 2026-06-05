import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "../LanguageSwitcher";
import type { DateFilter, Granularity } from "../../lib/dateFilter";
import { DateRangeFilter } from "./DateRangeFilter";
import { GranularityFilter } from "./GranularityFilter";

export type PageId = "overview" | "topics" | "trends" | "sources" | "pricing";

interface Props {
  page: PageId;
  onPage: (page: PageId) => void;
  filter: DateFilter;
  onFilter: (filter: DateFilter) => void;
  granularity: Granularity;
  onGranularity: (value: Granularity) => void;
  onSync: () => void;
  syncing: boolean;
}

const NAV: { id: PageId; icon: string }[] = [
  { id: "overview", icon: "◉" },
  { id: "topics", icon: "▦" },
  { id: "trends", icon: "↗" },
  { id: "sources", icon: "⎔" },
  { id: "pricing", icon: "$" },
];

export function Sidebar({
  page,
  onPage,
  filter,
  onFilter,
  granularity,
  onGranularity,
  onSync,
  syncing,
}: Props) {
  const { t } = useTranslation();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>{t("app.title")}</h1>
        <p className="sidebar-subtitle">{t("app.subtitle")}</p>
      </div>

      <button
        type="button"
        className="sidebar-sync"
        disabled={syncing}
        onClick={onSync}
      >
        {syncing ? t("toolbar.syncing") : t("toolbar.syncData")}
      </button>

      <nav className="sidebar-nav" aria-label={t("nav.label")}>
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            className={page === item.id ? "nav-item active" : "nav-item"}
            onClick={() => onPage(item.id)}
          >
            <span className="nav-icon" aria-hidden>
              {item.icon}
            </span>
            {t(`nav.${item.id}`)}
          </button>
        ))}
      </nav>

      <div className="sidebar-section">
        <DateRangeFilter filter={filter} onFilter={onFilter} compact />
        <GranularityFilter value={granularity} onChange={onGranularity} />
      </div>

      <div className="sidebar-footer">
        <LanguageSwitcher />
      </div>
    </aside>
  );
}

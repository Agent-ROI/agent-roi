import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { DateFilter, Granularity } from "../../lib/dateFilter";
import { DateRangeFilter } from "./DateRangeFilter";
import { GranularityFilter } from "./GranularityFilter";

export type PageId =
  | "overview"
  | "topics"
  | "activity"
  | "trends"
  | "sources"
  | "pricing"
  | "settings";

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

const NAV_ICONS: Record<PageId, ReactNode> = {
  overview: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" />
      <rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" />
    </svg>
  ),
  topics: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path d="M2 4h4M2 8h8M2 12h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="13" cy="4" r="1.5" fill="currentColor" />
      <circle cx="13" cy="8" r="1.5" fill="currentColor" />
      <circle cx="13" cy="12" r="1.5" fill="currentColor" />
    </svg>
  ),
  activity: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M10.5 2.5a3 3 0 00-3.9 3.6L2.5 10.2a1.4 1.4 0 102 2l4.1-4.1a3 3 0 003.6-3.9l-1.9 1.9-1.6-.4-.4-1.6 1.9-1.9z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  ),
  trends: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <polyline
        points="1,12 5,8 8,10 12,4 15,6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <polyline
        points="11,4 15,4 15,8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  ),
  sources: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" />
      <circle cx="8" cy="8" r="2" fill="currentColor" />
      <line x1="8" y1="2" x2="8" y2="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="8" y1="12" x2="8" y2="14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="2" y1="8" x2="4" y2="8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="12" y1="8" x2="14" y2="8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  pricing: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" />
      <path
        d="M8 4.5v1M8 10.5v1M6 7c0-.83.67-1.5 1.5-1.5h1C9.33 5.5 10 6.17 10 7S9.33 8.5 8.5 8.5h-1C6.67 8.5 6 9.17 6 10s.67 1.5 1.5 1.5h1c.83 0 1.5-.67 1.5-1.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  ),
  settings: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M6.86 2h2.28l.32 1.6a5 5 0 011.14.66l1.54-.52.98 1.7-1.22 1.08a5 5 0 010 1.32l1.22 1.08-.98 1.7-1.54-.52a5 5 0 01-1.14.66L9.14 14H6.86l-.32-1.6a5 5 0 01-1.14-.66l-1.54.52-.98-1.7 1.22-1.08a5 5 0 010-1.32L2.88 7.08l.98-1.7 1.54.52a5 5 0 011.14-.66L6.86 2z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
};

const NAV: { id: PageId }[] = [
  { id: "overview" },
  { id: "topics" },
  { id: "activity" },
  { id: "trends" },
  { id: "sources" },
  { id: "pricing" },
  { id: "settings" },
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
            <span className="nav-icon">{NAV_ICONS[item.id]}</span>
            {t(`nav.${item.id}`)}
          </button>
        ))}
      </nav>

      <div className="sidebar-section">
        <DateRangeFilter filter={filter} onFilter={onFilter} compact />
        <GranularityFilter value={granularity} onChange={onGranularity} />
      </div>

    </aside>
  );
}

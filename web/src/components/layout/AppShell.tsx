import type { ReactNode } from "react";
import type { DateFilter, Granularity } from "../../lib/dateFilter";
import { Sidebar, type PageId } from "./Sidebar";

interface Props {
  page: PageId;
  onPage: (page: PageId) => void;
  filter: DateFilter;
  onFilter: (filter: DateFilter) => void;
  granularity: Granularity;
  onGranularity: (value: Granularity) => void;
  onSync: () => void;
  syncing: boolean;
  children: ReactNode;
}

export function AppShell({
  page,
  onPage,
  filter,
  onFilter,
  granularity,
  onGranularity,
  onSync,
  syncing,
  children,
}: Props) {
  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        onPage={onPage}
        filter={filter}
        onFilter={onFilter}
        granularity={granularity}
        onGranularity={onGranularity}
        onSync={onSync}
        syncing={syncing}
      />
      <main className="main-content">{children}</main>
    </div>
  );
}

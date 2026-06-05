import type { ReactNode } from "react";
import { Sidebar, type PageId } from "./Sidebar";

interface Props {
  page: PageId;
  onPage: (page: PageId) => void;
  since: string;
  onSince: (value: string) => void;
  onSync: () => void;
  syncing: boolean;
  children: ReactNode;
}

export function AppShell({
  page,
  onPage,
  since,
  onSince,
  onSync,
  syncing,
  children,
}: Props) {
  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        onPage={onPage}
        since={since}
        onSince={onSince}
        onSync={onSync}
        syncing={syncing}
      />
      <main className="main-content">{children}</main>
    </div>
  );
}

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { api } from "./lib/api";
import { AppShell } from "./components/layout/AppShell";
import type { PageId } from "./components/layout/Sidebar";
import { OverviewPage } from "./pages/OverviewPage";
import { TopicsPage } from "./pages/TopicsPage";
import { TrendsPage } from "./pages/TrendsPage";
import { SourcesPage } from "./pages/SourcesPage";
import { PricingPage } from "./pages/PricingPage";
import { BreakdownModal } from "./components/BreakdownModal";

export default function App() {
  const { t } = useTranslation();
  const [page, setPage] = useState<PageId>("overview");
  const [since, setSince] = useState("");
  const [drillTopic, setDrillTopic] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [syncing, setSyncing] = useState(false);

  const refresh = useCallback(async () => {
    setVersion((v) => v + 1);
  }, []);

  const sync = useCallback(async () => {
    setSyncing(true);
    try {
      await api.refresh();
      await refresh();
    } catch (e) {
      console.error(e instanceof Error ? e.message : t("toolbar.error"));
    } finally {
      setSyncing(false);
    }
  }, [refresh, t]);

  return (
    <>
      <AppShell
        page={page}
        onPage={setPage}
        since={since}
        onSince={setSince}
        onSync={() => void sync()}
        syncing={syncing}
      >
        {page === "overview" && (
          <OverviewPage since={since} onDrillTopic={setDrillTopic} />
        )}
        {page === "topics" && (
          <TopicsPage since={since} onDrillTopic={setDrillTopic} />
        )}
        {page === "trends" && <TrendsPage since={since} />}
        {page === "sources" && (
          <SourcesPage reloadKey={version} onRefresh={refresh} />
        )}
        {page === "pricing" && <PricingPage />}
      </AppShell>

      {drillTopic && (
        <BreakdownModal
          topic={drillTopic}
          since={since}
          onClose={() => setDrillTopic(null)}
        />
      )}
    </>
  );
}

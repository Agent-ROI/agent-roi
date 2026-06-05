import { useEffect, useState, useCallback } from "react";
import { api, type TopicRollup } from "./lib/api";
import { fmtUsd } from "./lib/format";
import { TopicChart } from "./components/TopicChart";
import { TopicTable } from "./components/TopicTable";
import { Toolbar } from "./components/Toolbar";

export default function App() {
  const [topics, setTopics] = useState<TopicRollup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTopics(await api.topics());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const totalCost = topics.reduce((sum, t) => sum + t.cost_usd, 0);
  const totalTokens = topics.reduce((sum, t) => sum + t.total_tokens, 0);

  return (
    <div className="app">
      <header>
        <h1>Agent-ROI</h1>
        <p className="subtitle">Token cost &amp; ROI across your AI coding agents</p>
      </header>

      <Toolbar onRefresh={refresh} />

      {error && <div className="error">⚠ {error}</div>}

      <section className="stats">
        <div className="stat">
          <div className="stat-label">Total Cost</div>
          <div className="stat-value">{fmtUsd(totalCost)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Total Tokens</div>
          <div className="stat-value">{new Intl.NumberFormat().format(totalTokens)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Topics</div>
          <div className="stat-value">{topics.length}</div>
        </div>
      </section>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : topics.length === 0 ? (
        <p className="muted">No data yet. Run ingest, then classify.</p>
      ) : (
        <>
          <TopicChart topics={topics} />
          <TopicTable topics={topics} />
        </>
      )}
    </div>
  );
}

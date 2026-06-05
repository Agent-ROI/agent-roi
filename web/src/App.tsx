import { useEffect, useState, useCallback } from "react";
import { api, type Rollup, type Dimension } from "./lib/api";
import { fmtTokens, fmtUsd } from "./lib/format";
import { Controls } from "./components/Controls";
import { Toolbar } from "./components/Toolbar";
import { RollupChart } from "./components/RollupChart";
import { RollupTable } from "./components/RollupTable";
import { BreakdownModal } from "./components/BreakdownModal";
import { PricingModal } from "./components/PricingModal";

export default function App() {
  const [dimension, setDimension] = useState<Dimension>("topic");
  const [since, setSince] = useState<string>("");
  const [rows, setRows] = useState<Rollup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drillTopic, setDrillTopic] = useState<string | null>(null);
  const [showPricing, setShowPricing] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(await api.report(dimension, since));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [dimension, since]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const totalCost = rows.reduce((sum, r) => sum + r.cost_usd, 0);
  const totalTokens = rows.reduce((sum, r) => sum + r.total_tokens, 0);
  const anyEstimated = rows.some((r) => r.estimated);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Agent-ROI</h1>
          <p className="subtitle">Token cost &amp; ROI across your AI coding agents</p>
        </div>
        <button className="chip" onClick={() => setShowPricing(true)}>
          View pricing
        </button>
      </header>

      <Toolbar onRefresh={refresh} />
      <Controls
        dimension={dimension}
        onDimension={setDimension}
        since={since}
        onSince={setSince}
      />

      {error && <div className="error">⚠ {error}</div>}

      <section className="stats">
        <div className="stat">
          <div className="stat-label">Total Cost</div>
          <div className="stat-value">{fmtUsd(totalCost)}</div>
          {anyEstimated && <div className="stat-foot est">includes estimates</div>}
        </div>
        <div className="stat">
          <div className="stat-label">Total Tokens</div>
          <div className="stat-value">{fmtTokens(totalTokens)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">{dimension}s</div>
          <div className="stat-value">{rows.length}</div>
        </div>
      </section>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="muted">No data in this range. Run ingest, then classify.</p>
      ) : (
        <>
          <RollupChart rows={rows} dimension={dimension} />
          <RollupTable rows={rows} dimension={dimension} onDrill={setDrillTopic} />
        </>
      )}

      {drillTopic && (
        <BreakdownModal topic={drillTopic} since={since} onClose={() => setDrillTopic(null)} />
      )}
      {showPricing && <PricingModal onClose={() => setShowPricing(false)} />}
    </div>
  );
}

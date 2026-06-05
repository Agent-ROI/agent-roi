import { useState } from "react";
import { api } from "../lib/api";

interface Props {
  onRefresh: () => Promise<void>;
}

// Runs ingest/classify against the backend, then refreshes the dashboard.
export function Toolbar({ onRefresh }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setNote(null);
    try {
      const result = (await fn()) as Record<string, number>;
      const [[key, value]] = Object.entries(result);
      setNote(`${key}: ${value}`);
      await onRefresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="toolbar">
      <button disabled={!!busy} onClick={() => run("ingest", api.ingest)}>
        {busy === "ingest" ? "Ingesting…" : "Ingest"}
      </button>
      <button disabled={!!busy} onClick={() => run("classify", api.classify)}>
        {busy === "classify" ? "Classifying…" : "Classify"}
      </button>
      <button disabled={!!busy} onClick={() => void onRefresh()}>
        Refresh
      </button>
      {note && <span className="note">{note}</span>}
    </div>
  );
}

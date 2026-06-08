import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";

interface Props {
  onRefresh: () => Promise<void>;
}

export function Toolbar({ onRefresh }: Props) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setNote(null);
    try {
      const result = (await fn()) as Record<string, number>;
      const summary = Object.entries(result)
        .map(([k, v]) => `${t(`toolbar.${k}`, { defaultValue: k })}: ${v}`)
        .join(" · ");
      setNote(summary);
      await onRefresh();
    } catch (e) {
      setNote(e instanceof Error ? e.message : t("toolbar.error"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="toolbar">
      <button disabled={!!busy} onClick={() => run("ingest", api.ingest)}>
        {busy === "ingest" ? t("toolbar.ingesting") : t("toolbar.ingestOnly")}
      </button>
      <button className="ghost" disabled={!!busy} onClick={() => run("classify", api.classify)}>
        {busy === "classify" ? t("toolbar.classifying") : t("toolbar.reclassify")}
      </button>
      <button className="ghost" disabled={!!busy} onClick={() => void onRefresh()}>
        {t("toolbar.refreshView")}
      </button>
      {note && <span className="note">{note}</span>}
    </div>
  );
}

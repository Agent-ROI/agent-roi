import { useTranslation } from "react-i18next";
import { Toolbar } from "../components/Toolbar";
import { SourcesPanel } from "../components/SourcesPanel";

interface Props {
  reloadKey: number;
  onRefresh: () => Promise<void>;
}

export function SourcesPage({ reloadKey, onRefresh }: Props) {
  const { t } = useTranslation();

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.sources")}</h2>
        <p className="muted">{t("pages.sourcesHint")}</p>
      </header>
      <Toolbar onRefresh={onRefresh} />
      <SourcesPanel reloadKey={reloadKey} />
    </div>
  );
}

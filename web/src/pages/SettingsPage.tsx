import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGS, normalizeLng } from "../i18n";
import { api, type ConfigInfo } from "../lib/api";
import { toolDisplayName } from "../components/ToolIcon";

const ALL_COLLECTORS = ["claude_code", "codex", "copilot", "gemini", "hermes", "antigravity"];

// "" in a budget input means "no limit" (null on the backend).
const numOrNull = (v: string): number | null => {
  const n = parseFloat(v);
  return v.trim() === "" || Number.isNaN(n) ? null : n;
};
const strOrEmpty = (v: number | null): string => (v === null ? "" : String(v));

interface FormState {
  threshold: number;
  labelTerms: number;
  enabledCollectors: string[];
  daily: string;
  weekly: string;
  monthly: string;
}

function formFromConfig(cfg: ConfigInfo): FormState {
  return {
    threshold: cfg.classifier.similarity_threshold,
    labelTerms: cfg.classifier.label_terms,
    enabledCollectors: cfg.collectors.enabled,
    daily: strOrEmpty(cfg.budget?.daily_usd ?? null),
    weekly: strOrEmpty(cfg.budget?.weekly_usd ?? null),
    monthly: strOrEmpty(cfg.budget?.monthly_usd ?? null),
  };
}

const DEFAULT_FORM: FormState = {
  threshold: 0.18,
  labelTerms: 3,
  enabledCollectors: [],
  daily: "",
  weekly: "",
  monthly: "",
};

export function SettingsPage() {
  const { t, i18n } = useTranslation();
  const currentLang = normalizeLng(i18n.language);

  const [config, setConfig] = useState<ConfigInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);

  useEffect(() => {
    api
      .getConfig()
      .then((cfg) => {
        setConfig(cfg);
        setForm(formFromConfig(cfg));
      })
      .catch((e) => setError(e instanceof Error ? e.message : t("common.failed")))
      .finally(() => setLoading(false));
  }, [t]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api.updateConfig({
        classifier: { similarity_threshold: form.threshold, label_terms: form.labelTerms },
        collectors: { enabled: form.enabledCollectors },
        budget: {
          daily_usd: numOrNull(form.daily),
          weekly_usd: numOrNull(form.weekly),
          monthly_usd: numOrNull(form.monthly),
        },
      });
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.failed"));
    } finally {
      setSaving(false);
    }
  }, [form, t]);

  const toggleCollector = (name: string) => {
    setForm((prev) => ({
      ...prev,
      enabledCollectors: prev.enabledCollectors.includes(name)
        ? prev.enabledCollectors.filter((c) => c !== name)
        : [...prev.enabledCollectors, name],
    }));
  };

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("nav.settings")}</h2>
        <p className="muted">{t("pages.settingsHint")}</p>
      </header>

      {error && <div className="error">⚠ {error}</div>}
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : (
        <div className="settings-grid">
          <section className="settings-section">
            <h3>{t("settings.language")}</h3>
            <div className="settings-field">
              <label className="control-label" htmlFor="lang-select">
                {t("lang.label")}
              </label>
              <select
                id="lang-select"
                className="settings-select"
                value={SUPPORTED_LANGS.includes(currentLang) ? currentLang : "en"}
                onChange={(e) => void i18n.changeLanguage(e.target.value)}
              >
                {SUPPORTED_LANGS.map((code) => (
                  <option key={code} value={code}>
                    {t(`lang.${code}`)}
                  </option>
                ))}
              </select>
            </div>
          </section>

          <section className="settings-section">
            <h3>{t("settings.classifier")}</h3>
            <div className="settings-field">
              <label className="control-label" htmlFor="threshold">
                {t("settings.threshold")}
              </label>
              <div className="settings-range-row">
                <input
                  id="threshold"
                  type="range"
                  min="0.05"
                  max="0.5"
                  step="0.01"
                  value={form.threshold}
                  onChange={(e) => setForm((f) => ({ ...f, threshold: parseFloat(e.target.value) }))}
                />
                <span className="settings-range-value">{form.threshold.toFixed(2)}</span>
              </div>
              <p className="muted small">{t("settings.thresholdHint")}</p>
            </div>
            <div className="settings-field">
              <label className="control-label" htmlFor="label-terms">
                {t("settings.labelTerms")}
              </label>
              <input
                id="label-terms"
                type="number"
                className="settings-input"
                min={1}
                max={10}
                value={form.labelTerms}
                onChange={(e) => setForm((f) => ({ ...f, labelTerms: parseInt(e.target.value, 10) || 3 }))}
              />
              <p className="muted small">{t("settings.labelTermsHint")}</p>
            </div>
          </section>

          <section className="settings-section">
            <h3>{t("settings.collectors")}</h3>
            <div className="settings-checkbox-group">
              {ALL_COLLECTORS.map((name) => (
                <label key={name} className="settings-checkbox">
                  <input
                    type="checkbox"
                    checked={form.enabledCollectors.includes(name)}
                    onChange={() => toggleCollector(name)}
                  />
                  <span>{toolDisplayName(name)}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="settings-section">
            <h3>{t("settings.budget")}</h3>
            <p className="muted small">{t("settings.budgetHint")}</p>
            <div className="settings-budget-row">
              <div className="settings-field">
                <label className="control-label" htmlFor="budget-daily">
                  {t("budget.period.day")}
                </label>
                <input
                  id="budget-daily"
                  type="number"
                  className="settings-input"
                  min={0}
                  step="0.5"
                  placeholder={t("settings.budgetNone")}
                  value={form.daily}
                  onChange={(e) => setForm((f) => ({ ...f, daily: e.target.value }))}
                />
              </div>
              <div className="settings-field">
                <label className="control-label" htmlFor="budget-weekly">
                  {t("budget.period.week")}
                </label>
                <input
                  id="budget-weekly"
                  type="number"
                  className="settings-input"
                  min={0}
                  step="1"
                  placeholder={t("settings.budgetNone")}
                  value={form.weekly}
                  onChange={(e) => setForm((f) => ({ ...f, weekly: e.target.value }))}
                />
              </div>
              <div className="settings-field">
                <label className="control-label" htmlFor="budget-monthly">
                  {t("budget.period.month")}
                </label>
                <input
                  id="budget-monthly"
                  type="number"
                  className="settings-input"
                  min={0}
                  step="1"
                  placeholder={t("settings.budgetNone")}
                  value={form.monthly}
                  onChange={(e) => setForm((f) => ({ ...f, monthly: e.target.value }))}
                />
              </div>
            </div>
          </section>

          <section className="settings-section">
            <h3>{t("settings.paths")}</h3>
            <div className="settings-field">
              <span className="control-label">{t("settings.configPath")}</span>
              <code className="settings-path">{config?.config_path}</code>
            </div>
            <div className="settings-field">
              <span className="control-label">{t("settings.dbPath")}</span>
              <code className="settings-path">{config?.db_path}</code>
            </div>
          </section>

          <div className="settings-actions">
            <button
              type="button"
              className="btn-primary"
              disabled={saving}
              onClick={() => void handleSave()}
            >
              {saving ? t("settings.saving") : t("settings.save")}
            </button>
            {saved && <span className="settings-saved">{t("settings.saved")}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

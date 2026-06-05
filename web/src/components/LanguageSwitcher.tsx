import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGS, normalizeLng } from "../i18n";

// Language picker matching the 11 supported locales. Choice persists in
// localStorage under agent-roi-lang.
export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = normalizeLng(i18n.language);

  return (
    <label className="lang-switcher">
      <span className="control-label">{t("lang.label")}</span>
      <select
        className="lang-select"
        value={SUPPORTED_LANGS.includes(current) ? current : "en"}
        onChange={(e) => void i18n.changeLanguage(e.target.value)}
        aria-label={t("lang.label")}
      >
        {SUPPORTED_LANGS.map((code) => (
          <option key={code} value={code}>
            {t(`lang.${code}`)}
          </option>
        ))}
      </select>
    </label>
  );
}

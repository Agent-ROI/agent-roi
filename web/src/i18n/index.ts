import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./locales/en.json";
import zhCN from "./locales/zh-CN.json";
import zhTW from "./locales/zh-TW.json";
import ja from "./locales/ja.json";
import de from "./locales/de.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";
import tr from "./locales/tr.json";
import uk from "./locales/uk.json";
import af from "./locales/af.json";
import ko from "./locales/ko.json";

export const SUPPORTED_LANGS = [
  "en",
  "zh-CN",
  "zh-TW",
  "ja",
  "de",
  "es",
  "fr",
  "tr",
  "uk",
  "af",
  "ko",
] as const;

export type LangCode = (typeof SUPPORTED_LANGS)[number];

/** Map browser locale tags to our supported codes. */
export function normalizeLng(lng: string): LangCode {
  const lower = lng.toLowerCase();
  if (lower.startsWith("zh-tw") || lower.startsWith("zh-hant")) return "zh-TW";
  if (lower.startsWith("zh-cn") || lower.startsWith("zh-hans") || lower === "zh") return "zh-CN";
  const base = lng.split("-")[0] as LangCode;
  if ((SUPPORTED_LANGS as readonly string[]).includes(base)) return base;
  if ((SUPPORTED_LANGS as readonly string[]).includes(lng)) return lng as LangCode;
  return "en";
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      "zh-CN": { translation: zhCN },
      "zh-TW": { translation: zhTW },
      ja: { translation: ja },
      de: { translation: de },
      es: { translation: es },
      fr: { translation: fr },
      tr: { translation: tr },
      uk: { translation: uk },
      af: { translation: af },
      ko: { translation: ko },
    },
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "agent-roi-lang",
      convertDetectedLanguage: normalizeLng,
    },
  });

export default i18n;

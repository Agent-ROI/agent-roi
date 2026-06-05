import i18n, { normalizeLng } from "../i18n";

function locale(): string {
  const code = normalizeLng(i18n.language || "en");
  // Intl needs a BCP-47 tag; base codes like "ja" work as-is.
  if (code === "zh-CN" || code === "zh-TW") return code;
  return code;
}

export const fmtTokens = (n: number): string =>
  new Intl.NumberFormat(locale()).format(n);

export const fmtUsd = (n: number): string =>
  new Intl.NumberFormat(locale(), {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n);

export const fmtDateTime = (iso: string): string =>
  new Date(iso).toLocaleString(locale());

export const fmtTime = (iso: string): string =>
  new Date(iso).toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });

/** Compact range; collapses to a single time when start ≈ end. */
export const fmtTimeRange = (start: string, end: string): string => {
  const s = new Date(start);
  const e = new Date(end);
  if (Math.abs(e.getTime() - s.getTime()) < 60_000) {
    return fmtDateTime(start);
  }
  const sameDay = s.toDateString() === e.toDateString();
  if (sameDay) {
    return `${s.toLocaleDateString(locale())} ${fmtTime(start)}–${fmtTime(end)}`;
  }
  return `${fmtDateTime(start)} – ${fmtDateTime(end)}`;
};

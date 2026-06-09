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

/** Active-time minutes → compact "1h 54m" / "47m" / "—" (0 is unmeasurable). */
export const fmtDuration = (minutes: number): string => {
  if (!minutes || minutes <= 0) return "—";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return h ? `${h}h ${m}m` : `${m}m`;
};

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

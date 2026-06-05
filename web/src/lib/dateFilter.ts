export type Granularity = "day" | "week" | "month";

export interface DateFilter {
  since: string;
  until: string;
}

export const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isCustomRange(filter: DateFilter): boolean {
  return ISO_DATE.test(filter.since) || ISO_DATE.test(filter.until);
}

export function rangeInvalid(filter: DateFilter): boolean {
  if (!ISO_DATE.test(filter.since) || !ISO_DATE.test(filter.until)) return false;
  return filter.since > filter.until;
}

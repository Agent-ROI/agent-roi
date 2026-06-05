export const fmtTokens = (n: number): string => new Intl.NumberFormat().format(n);

export const fmtUsd = (n: number): string =>
  new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(n);

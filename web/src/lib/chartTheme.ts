export const CHART_COLORS = [
  "#5645d4",
  "#1aae39",
  "#dd5b00",
  "#0075de",
  "#7b3ff2",
  "#2a9d99",
  "#ff64c8",
  "#787671",
] as const;

export const TOOL_COLORS: Record<string, string> = {
  claude_code: "#5645d4",
  copilot: "#1aae39",
  codex: "#dd5b00",
  gemini: "#0075de",
  cursor: "#7b3ff2",
  unknown: "#787671",
  other: "#a4a097",
};

export function seriesColor(key: string, index = 0): string {
  return TOOL_COLORS[key] ?? CHART_COLORS[index % CHART_COLORS.length];
}

export const chartTooltipStyle = {
  background: "#ffffff",
  border: "1px solid #e5e3df",
  borderRadius: 8,
  color: "#1a1a1a",
  boxShadow: "rgba(15, 15, 15, 0.08) 0px 4px 12px 0px",
};

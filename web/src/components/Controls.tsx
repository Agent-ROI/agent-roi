import type { Dimension } from "../lib/api";

interface Props {
  dimension: Dimension;
  onDimension: (d: Dimension) => void;
  since: string;
  onSince: (s: string) => void;
}

const DIMENSIONS: Dimension[] = ["topic", "tool", "model"];
const RANGES: { label: string; value: string }[] = [
  { label: "All time", value: "" },
  { label: "Today", value: "today" },
  { label: "7 days", value: "7d" },
  { label: "30 days", value: "30d" },
];

// Lets the user choose the grouping dimension and the time window. These drive
// every figure on the dashboard, so the numbers are always scoped explicitly.
export function Controls({ dimension, onDimension, since, onSince }: Props) {
  return (
    <div className="controls">
      <div className="control-group">
        <span className="control-label">Group by</span>
        {DIMENSIONS.map((d) => (
          <button
            key={d}
            className={d === dimension ? "chip active" : "chip"}
            onClick={() => onDimension(d)}
          >
            {d}
          </button>
        ))}
      </div>
      <div className="control-group">
        <span className="control-label">Range</span>
        {RANGES.map((r) => (
          <button
            key={r.value}
            className={r.value === since ? "chip active" : "chip"}
            onClick={() => onSince(r.value)}
          >
            {r.label}
          </button>
        ))}
      </div>
    </div>
  );
}

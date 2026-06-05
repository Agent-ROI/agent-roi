import type { Rollup, Dimension } from "../lib/api";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  rows: Rollup[];
  dimension: Dimension;
  onDrill?: (key: string) => void;
}

export function RollupTable({ rows, dimension, onDrill }: Props) {
  const sorted = rows.slice().sort((a, b) => b.cost_usd - a.cost_usd);
  const drillable = dimension === "topic" && !!onDrill;

  return (
    <section className="card">
      <h2>All {dimension}s</h2>
      <table>
        <thead>
          <tr>
            <th>{dimension}</th>
            <th className="num">Interactions</th>
            <th className="num">Input</th>
            <th className="num">Output</th>
            <th className="num">Total Tokens</th>
            <th className="num">Cost</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.key}
              className={drillable ? "drillable" : undefined}
              onClick={drillable ? () => onDrill!(r.key) : undefined}
              title={drillable ? "Click to see tool/model breakdown" : undefined}
            >
              <td>
                {r.key}
                {drillable && <span className="drill-hint"> ›</span>}
              </td>
              <td className="num">{r.interactions}</td>
              <td className="num">{fmtTokens(r.input_tokens)}</td>
              <td className="num">{fmtTokens(r.output_tokens)}</td>
              <td className="num">{fmtTokens(r.total_tokens)}</td>
              <td className="num cost">{fmtUsd(r.cost_usd)}</td>
              <td>
                <span className={r.estimated ? "badge est" : "badge exact"}>
                  {r.estimated ? "estimated" : "exact"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

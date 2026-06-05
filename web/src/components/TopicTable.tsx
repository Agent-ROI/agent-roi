import type { TopicRollup } from "../lib/api";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  topics: TopicRollup[];
}

export function TopicTable({ topics }: Props) {
  const sorted = topics.slice().sort((a, b) => b.cost_usd - a.cost_usd);

  return (
    <section className="card">
      <h2>All Topics</h2>
      <table>
        <thead>
          <tr>
            <th>Topic</th>
            <th className="num">Interactions</th>
            <th className="num">Input</th>
            <th className="num">Output</th>
            <th className="num">Total Tokens</th>
            <th className="num">Cost</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((t) => (
            <tr key={t.topic}>
              <td>{t.topic}</td>
              <td className="num">{t.interactions}</td>
              <td className="num">{fmtTokens(t.input_tokens)}</td>
              <td className="num">{fmtTokens(t.output_tokens)}</td>
              <td className="num">{fmtTokens(t.total_tokens)}</td>
              <td className="num cost">{fmtUsd(t.cost_usd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

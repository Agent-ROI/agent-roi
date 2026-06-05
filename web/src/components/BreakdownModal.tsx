import { useEffect, useState } from "react";
import { api, type TopicBreakdown, type Rollup } from "../lib/api";
import { fmtTokens, fmtUsd } from "../lib/format";

interface Props {
  topic: string;
  since: string;
  onClose: () => void;
}

// Drill-down: shows exactly which tools and models a topic's cost came from, so
// the headline number is traceable to its sources.
export function BreakdownModal({ topic, since, onClose }: Props) {
  const [data, setData] = useState<TopicBreakdown | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .topic(topic, since)
      .then((d) => active && setData(d))
      .catch((e) => active && setError(e instanceof Error ? e.message : "Failed"));
    return () => {
      active = false;
    };
  }, [topic, since]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{topic}</h2>
          <button className="chip" onClick={onClose}>
            ✕
          </button>
        </div>

        {error && <div className="error">⚠ {error}</div>}
        {!data ? (
          <p className="muted">Loading…</p>
        ) : (
          <>
            <p className="muted">
              {data.total.interactions} interactions · {fmtTokens(data.total.total_tokens)} tokens ·{" "}
              <strong>{fmtUsd(data.total.cost_usd)}</strong>
              {data.total.estimated && <span className="badge est"> includes estimates</span>}
            </p>
            <SplitTable title="By tool" rows={data.by_tool} total={data.total.cost_usd} />
            <SplitTable title="By model" rows={data.by_model} total={data.total.cost_usd} />
          </>
        )}
      </div>
    </div>
  );
}

function SplitTable({ title, rows, total }: { title: string; rows: Rollup[]; total: number }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      <table>
        <thead>
          <tr>
            <th>{title.replace("By ", "")}</th>
            <th className="num">Tokens</th>
            <th className="num">Cost</th>
            <th className="num">Share</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.key}</td>
              <td className="num">{fmtTokens(r.total_tokens)}</td>
              <td className="num cost">{fmtUsd(r.cost_usd)}</td>
              <td className="num">{total ? `${Math.round((r.cost_usd / total) * 100)}%` : "—"}</td>
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

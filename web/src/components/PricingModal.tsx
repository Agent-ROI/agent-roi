import { useEffect, useState } from "react";
import { api, type ModelPricing } from "../lib/api";

interface Props {
  onClose: () => void;
}

// Shows the pricing table behind every cost figure, so users can verify that
// cost = usage x these unit prices.
export function PricingModal({ onClose }: Props) {
  const [prices, setPrices] = useState<ModelPricing[] | null>(null);

  useEffect(() => {
    let active = true;
    api.pricing().then((p) => active && setPrices(p));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Model pricing</h2>
          <button className="chip" onClick={onClose}>
            ✕
          </button>
        </div>
        <p className="muted">USD per 1,000,000 tokens. Cost = usage × these unit prices.</p>
        {!prices ? (
          <p className="muted">Loading…</p>
        ) : (
          <section className="card">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th className="num">Input</th>
                  <th className="num">Output</th>
                  <th className="num">Cache read</th>
                  <th className="num">Cache write</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((p) => (
                  <tr key={p.model}>
                    <td>{p.model}</td>
                    <td className="num">${p.input}</td>
                    <td className="num">${p.output}</td>
                    <td className="num">${p.cache_read}</td>
                    <td className="num">${p.cache_write}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </div>
  );
}

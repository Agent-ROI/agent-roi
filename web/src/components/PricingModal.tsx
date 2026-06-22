import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ModelPricing } from "../lib/api";

interface Props {
  onClose: () => void;
}

export function PricingModal({ onClose }: Props) {
  const { t } = useTranslation();
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
          <h2>{t("pricing.title")}</h2>
          <button className="chip" onClick={onClose}>
            ✕
          </button>
        </div>
        <p className="muted">{t("pricing.subtitle")}</p>
        {!prices ? (
          <p className="muted">{t("common.loading")}</p>
        ) : (
          <section className="card">
            <table>
              <thead>
                <tr>
                  <th>{t("pricing.model")}</th>
                  <th>{t("pricing.provider")}</th>
                  <th>{t("pricing.promptSize")}</th>
                  <th className="num">{t("pricing.input")}</th>
                  <th className="num">{t("pricing.output")}</th>
                  <th className="num">{t("pricing.cacheRead")}</th>
                  <th className="num">{t("pricing.cacheWrite")}</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((p) => (
                  <tr key={`${p.model}-${p.provider ?? "any"}-${p.effective_from}-${p.tier_label}`}>
                    <td>{p.model}</td>
                    <td className="muted small">{p.provider ?? t("pricing.providerAny")}</td>
                    <td className="muted small">{p.tier_label || t("pricing.promptSizeAll")}</td>
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

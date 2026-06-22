import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, type ModelPricing } from "../lib/api";

export function PricingPage() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<ModelPricing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .pricing()
      .then((data) => active && setRows(data))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h2>{t("pricing.title")}</h2>
        <p className="muted">{t("pricing.subtitle")}</p>
      </header>
      {loading ? (
        <p className="muted">{t("common.loading")}</p>
      ) : (
        Object.entries(
          rows.reduce<Record<string, ModelPricing[]>>((acc, p) => {
            (acc[p.vendor] ??= []).push(p);
            return acc;
          }, {}),
        ).map(([vendor, group]) => (
          <section className="card" key={vendor}>
            <h3>{vendor}</h3>
            <table>
              <thead>
                <tr>
                  <th>{t("pricing.model")}</th>
                  <th>{t("pricing.provider")}</th>
                  <th>{t("pricing.promptSize")}</th>
                  <th>{t("pricing.effectiveFrom")}</th>
                  <th className="num">{t("pricing.input")}</th>
                  <th className="num">{t("pricing.output")}</th>
                  <th className="num">{t("pricing.cacheRead")}</th>
                  <th className="num">{t("pricing.cacheWrite")}</th>
                </tr>
              </thead>
              <tbody>
                {group.map((p) => (
                  <tr key={`${p.model}-${p.provider ?? "any"}-${p.effective_from}-${p.tier_label}`}>
                    <td>{p.model}</td>
                    <td className="muted small">{p.provider ?? t("pricing.providerAny")}</td>
                    <td className="muted small">{p.tier_label || t("pricing.promptSizeAll")}</td>
                    <td className="muted small">{p.effective_from}</td>
                    <td className="num">${p.input}</td>
                    <td className="num">${p.output}</td>
                    <td className="num">${p.cache_read}</td>
                    <td className="num">${p.cache_write}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        ))
      )}
    </div>
  );
}

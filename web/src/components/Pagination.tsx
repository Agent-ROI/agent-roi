import { useTranslation } from "react-i18next";

interface Props {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}

export function Pagination({ page, totalPages, onChange }: Props) {
  const { t } = useTranslation();
  return (
    <div className="pagination">
      <button
        className="chip"
        disabled={page === 0}
        onClick={() => onChange(page - 1)}
      >
        ‹
      </button>
      <span className="pagination-info">
        {t("pagination.pageOf", { page: page + 1, total: totalPages })}
      </span>
      <button
        className="chip"
        disabled={page >= totalPages - 1}
        onClick={() => onChange(page + 1)}
      >
        ›
      </button>
    </div>
  );
}

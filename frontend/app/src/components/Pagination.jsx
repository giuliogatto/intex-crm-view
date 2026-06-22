import React from 'react'

export default function Pagination({ page, pages, total, onPageChange, label }) {
  if (pages <= 1) return null

  return (
    <div className="pagination">
      <span className="pagination__info">
        {label}: pagina {page} di {pages} ({total} totali)
      </span>
      <div className="pagination__controls">
        <button
          type="button"
          className="btn"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Precedente
        </button>
        <button
          type="button"
          className="btn"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Successiva
        </button>
      </div>
    </div>
  )
}

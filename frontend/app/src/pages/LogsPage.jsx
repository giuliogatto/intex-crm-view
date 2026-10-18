import React, { useState, useEffect, useCallback } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import AdminNav from '../components/AdminNav'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 100

const EVENT_LABELS = {
  login: 'Login',
  search: 'Ricerca',
}

function formatDetails(eventType, details) {
  if (!details || typeof details !== 'object') return '—'

  if (eventType === 'login') {
    const ok = details.success ? 'ok' : 'fallito'
    const role = details.role ? ` · ${details.role}` : ''
    return `${ok}${role}`
  }

  if (eventType === 'search') {
    const filters = details.filters || {}
    const parts = Object.entries(filters)
      .filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0))
      .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join(',') : v}`)
    const total =
      details.result_total != null ? ` · ${details.result_total} risultati` : ''
    const pageInfo =
      details.page != null ? ` · p.${details.page}` : ''
    if (parts.length === 0) return `(nessun filtro)${total}${pageInfo}`
    return `${parts.join(' · ')}${total}${pageInfo}`
  }

  try {
    return JSON.stringify(details)
  } catch {
    return '—'
  }
}

export default function LogsPage() {
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [q, setQ] = useState('')
  const [eventType, setEventType] = useState('')
  const [qApplied, setQApplied] = useState('')
  const [eventTypeApplied, setEventTypeApplied] = useState('')

  const loadList = useCallback(() => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams({
      page: String(page),
      limit: String(PAGE_SIZE),
    })
    if (qApplied) params.set('q', qApplied)
    if (eventTypeApplied) params.set('event_type', eventTypeApplied)
    authFetch(`/api/admin/logs?${params}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Errore nel caricamento logs')
        setRows(data.data || [])
        setPages(data.pages || 1)
        setTotal(data.total || 0)
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
      })
      .finally(() => setLoading(false))
  }, [page, qApplied, eventTypeApplied])

  useEffect(() => {
    loadList()
  }, [loadList])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    setQApplied(q.trim())
    setEventTypeApplied(eventType)
  }

  const handleReset = () => {
    setQ('')
    setEventType('')
    setPage(1)
    setQApplied('')
    setEventTypeApplied('')
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-title-group">
          <a href="/" className="app-logo-link">
            <img src="/logo.webp" alt="Intex" className="app-logo" />
          </a>
          <span className="badge-mock">Logs di accesso</span>
        </div>
        <div className="app-header__actions">
          <UserMenu />
          <AdminNav />
          <a href="/" className="btn">
            ← Torna alla consultazione
          </a>
        </div>
      </header>

      <div className="logs-page">
        <div className="panel logs-list-panel">
          <div className="panel__head">
            <span>Eventi ({total})</span>
          </div>
          <div className="panel__body panel__body--compact">
            <form className="sinonimi-filters" onSubmit={handleSearch}>
              <label className="users-form__field" style={{ flex: 1, minWidth: 200 }}>
                <span>Cerca</span>
                <input
                  type="search"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Utente, IP, dettagli, id…"
                />
              </label>
              <label className="users-form__field" style={{ minWidth: 140 }}>
                <span>Tipo</span>
                <select value={eventType} onChange={(e) => setEventType(e.target.value)}>
                  <option value="">Tutti</option>
                  <option value="login">Login</option>
                  <option value="search">Ricerca</option>
                </select>
              </label>
              <button type="submit" className="btn btn--primary btn--sm" style={{ alignSelf: 'flex-end' }}>
                Filtra
              </button>
              <button
                type="button"
                className="btn btn--sm"
                style={{ alignSelf: 'flex-end' }}
                onClick={handleReset}
              >
                Reset
              </button>
            </form>

            {loading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento logs...</span>
              </div>
            ) : error ? (
              <p className="users-empty users-empty--error">{error}</p>
            ) : rows.length === 0 ? (
              <p className="users-empty">Nessun log trovato.</p>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="data chats-table logs-table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Tipo</th>
                        <th>Utente</th>
                        <th>Dettagli</th>
                        <th>IP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.id} className="chats-table__row">
                          <td className="logs-table__nowrap">{row.created_at}</td>
                          <td>
                            <span className={`logs-badge logs-badge--${row.event_type}`}>
                              {EVENT_LABELS[row.event_type] || row.event_type}
                            </span>
                          </td>
                          <td>{row.username || '—'}</td>
                          <td className="logs-table__details" title={formatDetails(row.event_type, row.details)}>
                            {formatDetails(row.event_type, row.details)}
                          </td>
                          <td className="logs-table__nowrap">{row.ip || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <Pagination
                  page={page}
                  pages={pages}
                  total={total}
                  onPageChange={setPage}
                  label="Logs"
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

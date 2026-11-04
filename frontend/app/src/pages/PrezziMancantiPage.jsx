import React, { useCallback, useEffect, useState } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import DateInput from '../components/DateInput'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 100

function todayISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function monthStartISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}-01`
}

function formatIt(iso) {
  if (!iso) return '—'
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!m) return iso
  return `${m[3]}/${m[2]}/${m[1]}`
}

function formatQty(n) {
  const v = Number(n) || 0
  return v.toLocaleString('it-IT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 3,
  })
}

export default function PrezziMancantiPage() {
  const [dataDaFilter, setDataDaFilter] = useState(monthStartISO())
  const [dataAFilter, setDataAFilter] = useState(todayISO())
  const [dataDaApplied, setDataDaApplied] = useState('')
  const [dataAApplied, setDataAApplied] = useState('')
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [range, setRange] = useState({ da: '', a: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  const loadList = useCallback(() => {
    if (!dataDaApplied || !dataAApplied) return
    setLoading(true)
    setError('')
    const params = new URLSearchParams({
      data_da: dataDaApplied,
      data_a: dataAApplied,
      page: String(page),
      limit: String(PAGE_SIZE),
    })
    authFetch(`/api/admin/prezzi-mancanti?${params}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.error || 'Errore nel caricamento')
        setRows(data.data || [])
        setPages(data.pages || 1)
        setTotal(data.total || 0)
        setRange({ da: data.data_da || '', a: data.data_a || '' })
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
        setRows([])
        setTotal(0)
        setPages(1)
      })
      .finally(() => setLoading(false))
  }, [dataDaApplied, dataAApplied, page])

  useEffect(() => {
    loadList()
  }, [loadList])

  const handleSearch = (e) => {
    e.preventDefault()
    if (!dataDaFilter || !dataAFilter) {
      setError('Seleziona data da e data a')
      return
    }
    if (dataDaFilter > dataAFilter) {
      setError('La data da non può essere successiva alla data a')
      return
    }
    setSearched(true)
    setPage(1)
    setDataDaApplied(dataDaFilter)
    setDataAApplied(dataAFilter)
  }

  const handleReset = () => {
    setDataDaFilter(monthStartISO())
    setDataAFilter(todayISO())
    setDataDaApplied('')
    setDataAApplied('')
    setSearched(false)
    setRows([])
    setTotal(0)
    setPages(1)
    setPage(1)
    setError('')
    setRange({ da: '', a: '' })
  }

  return (
    <div className="app-container">
      <div className="app-sticky-top">
        <header className="app-header">
          <div className="app-title-group">
            <a href="/" className="app-logo-link">
              <img src="/logo.webp" alt="Intex" className="app-logo" />
            </a>
          </div>
          <div className="app-header__actions">
            <UserMenu />
          </div>
        </header>

        <nav className="nav-primary" aria-label="Navigazione principale">
          <a href="/" className="nav-tab">
            📦 Consultazione
          </a>
          <a href="/prezzi-mancanti" className="nav-tab is-active" aria-current="page">
            💶 Prezzi mancanti
          </a>
        </nav>
      </div>

      <div className="logs-page prezzi-mancanti-page">
        <div className="panel logs-list-panel">
          <div className="panel__head">
            <span>
              Lista controllo prezzi mancanti
              {searched ? ` (${total})` : ''}
            </span>
          </div>
          <div className="panel__body panel__body--compact">
            <form className="sinonimi-filters" onSubmit={handleSearch}>
              <label className="users-form__field" style={{ minWidth: 200 }}>
                <span>Data da</span>
                <DateInput
                  name="data_da"
                  value={dataDaFilter}
                  onChange={(e) => setDataDaFilter(e.target.value)}
                  placeholder="Seleziona data inizio…"
                />
              </label>
              <label className="users-form__field" style={{ minWidth: 200 }}>
                <span>Data a</span>
                <DateInput
                  name="data_a"
                  value={dataAFilter}
                  onChange={(e) => setDataAFilter(e.target.value)}
                  placeholder="Seleziona data fine…"
                />
              </label>
              <button type="submit" className="btn btn--primary btn--sm" style={{ alignSelf: 'flex-end' }}>
                Cerca
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

            <p className="sinonimi-hint">
              Mostra le spedizioni (DDT di uscita) nel periodo selezionato
              con ciclo senza prezzo associato in disposizione (come il report Wash).
              {range.da && range.a ? (
                <>
                  {' '}
                  Periodo: <strong>{formatIt(range.da)}</strong> – <strong>{formatIt(range.a)}</strong>.
                </>
              ) : null}
            </p>

            {loading ? (
              <div className="loading-indicator">
                <div className="spinner" />
                <span>Caricamento prezzi mancanti…</span>
              </div>
            ) : error ? (
              <p className="users-empty users-empty--error">{error}</p>
            ) : !searched ? (
              <p className="users-empty">Seleziona il periodo e premi Cerca.</p>
            ) : rows.length === 0 ? (
              <p className="users-empty">Nessuna riga senza prezzo nel periodo.</p>
            ) : (
              <>
                <div className="table-wrap prezzi-mancanti-table-wrap">
                  <table className="data chats-table prezzi-mancanti-table">
                    <thead>
                      <tr>
                        <th>Cliente</th>
                        <th>Ns. DDT</th>
                        <th>Data DDT</th>
                        <th>Tipo</th>
                        <th>Articolo</th>
                        <th>Linea</th>
                        <th>Stag. listino</th>
                        <th>Stag. prod.</th>
                        <th>Composizione</th>
                        <th>Ns. disposiz.</th>
                        <th>Ciclo</th>
                        <th>Ciclo lavoro</th>
                        <th className="prezzi-mancanti-table__num">Capi</th>
                        <th className="prezzi-mancanti-table__num">Kg</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, idx) => (
                        <tr
                          key={`${row.ns_ddt}-${row.ns_disposiz}-${idx}`}
                          className="chats-table__row"
                        >
                          <td title={row.cliente}>{row.cliente}</td>
                          <td className="logs-table__nowrap">{row.ns_ddt}</td>
                          <td className="logs-table__nowrap">{row.data_ddt}</td>
                          <td>{row.tipo}</td>
                          <td title={row.articolo}>{row.articolo}</td>
                          <td title={row.linea}>{row.linea || '—'}</td>
                          <td>{row.stagione_listino || '—'}</td>
                          <td>{row.stagione_produzione || '—'}</td>
                          <td title={row.composizione}>{row.composizione || '—'}</td>
                          <td className="logs-table__nowrap">{row.ns_disposiz}</td>
                          <td className="logs-table__nowrap">{row.ciclo}</td>
                          <td title={row.ciclo_lavoro}>{row.ciclo_lavoro || '—'}</td>
                          <td className="prezzi-mancanti-table__num">{formatQty(row.capi_sped)}</td>
                          <td className="prezzi-mancanti-table__num">{formatQty(row.kg_sped)}</td>
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
                  label="Righe"
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

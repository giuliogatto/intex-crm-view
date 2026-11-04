import React, { useCallback, useEffect, useRef, useState } from 'react'
import { authFetch } from '../utils/auth'
import UserMenu from '../components/UserMenu'
import DateInput from '../components/DateInput'
import Pagination from '../components/Pagination'

const PAGE_SIZE = 100
const DEFAULT_LIVELLO = 4
const COL_COUNT = 14

const LIVELLO_HINT = {
  1: 'ampio (≥30%)',
  2: 'medio (≥50%)',
  3: 'alto (≥70%)',
  4: 'molto alto (≥90%)',
  5: 'equivalenti (100%)',
}

const CAMPO_LABELS = {
  codice_articolo: 'Articolo',
  codice_stagione: 'Stagione',
  codice_ciclo: 'Cod. ciclo',
  codice_ciclo_cli: 'Ciclo cliente',
  codice_composizione: 'Composizione',
  codice_linea: 'Linea',
  ds_ciclo: 'Descrizione ciclo',
  ds_ciclo_bolle_fat: 'Desc. bolle/fatt.',
  note: 'Note',
  ds_applicazione: 'Applicazione',
  ds_ricamo: 'Ricamo',
  ds_stampa: 'Stampa',
  codice_reparto: 'Reparto',
  codice_gruppo: 'Gruppo',
  fase: 'Fase',
  nota_fase: 'Nota fase',
  unita_misura_fase: 'U.M. fase',
  macrofase: 'Macrofase',
}

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

function campoLabel(campo) {
  return CAMPO_LABELS[campo] || campo
}

function formatVal(v) {
  if (v == null || v === '') return '—'
  if (Array.isArray(v)) return v.filter(Boolean).join(' → ') || '—'
  return String(v)
}

function rowKey(row, idx) {
  return [
    row.ns_ddt,
    row.ns_disposiz,
    row.codice_cliente,
    row.codice_articolo,
    row.codice_ciclo,
    row.codice_linea,
    row.codice_stagione,
    row.codice_composizione,
    idx,
  ].join('|')
}

function cicloPayload(row, id) {
  return {
    id,
    codice_cliente: row.codice_cliente || '',
    codice_articolo: row.codice_articolo || '',
    codice_ciclo: row.codice_ciclo || row.ciclo || '',
    codice_linea: row.codice_linea || '',
    codice_stagione: row.codice_stagione || '',
    codice_composizione: row.codice_composizione || '',
  }
}

function CompatPct({ value }) {
  const v = Number(value) || 0
  let tone = 'low'
  if (v >= 90) tone = 'high'
  else if (v >= 70) tone = 'mid'
  return (
    <span className={`pm-compat-pct pm-compat-pct--${tone}`} title={`${v}%`}>
      {v.toLocaleString('it-IT', { maximumFractionDigits: 1 })}%
    </span>
  )
}

function DiffList({ items }) {
  if (!items?.length) return <span className="pm-compat-empty">nessuna</span>
  return (
    <ul className="pm-compat-chips pm-compat-chips--diff">
      {items.map((d, i) => (
        <li key={`${d.campo}-${i}`}>
          <span className="pm-compat-chip__field">{campoLabel(d.campo)}</span>
          {d.tipo ? <span className="pm-compat-chip__tipo">{d.tipo}</span> : null}
          <span className="pm-compat-chip__vals">
            {formatVal(d.input)}
            <span aria-hidden="true"> → </span>
            {formatVal(d.candidato)}
          </span>
          {d.penalita != null && Number(d.penalita) > 0 ? (
            <span className="pm-compat-chip__pen">−{d.penalita}</span>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

function SimiliList({ items }) {
  if (!items?.length) return <span className="pm-compat-empty">nessuna</span>
  return (
    <ul className="pm-compat-chips pm-compat-chips--simili">
      {items.map((s, i) => (
        <li key={`${s.campo}-${i}`}>
          <span className="pm-compat-chip__field">{campoLabel(s.campo)}</span>
          <span className="pm-compat-chip__vals">{formatVal(s.valore)}</span>
          {s.dettaglio ? <span className="pm-compat-chip__note">{s.dettaglio}</span> : null}
        </li>
      ))}
    </ul>
  )
}

function CicliCompatibiliPanel({
  rowId,
  stato,
  livello,
  onLivelloChange,
}) {
  const loading = !stato || stato.loading
  const error = stato?.error
  const compatibili = stato?.compatibili || []
  const soglia = stato?.soglia

  return (
    <div className="pm-compat">
      <div className="pm-compat__head">
        <div className="pm-compat__title">
          <span className="pm-compat__badge">Cicli compatibili</span>
          <span className="pm-compat__meta">
            livello {livello} · {LIVELLO_HINT[livello] || ''}
            {soglia != null ? ` · soglia ${soglia}%` : ''}
          </span>
        </div>
        <label className="pm-compat__slider">
          <span>Livello ricerca</span>
          <input
            type="range"
            min={1}
            max={5}
            step={1}
            value={livello}
            disabled={loading}
            onChange={(e) => onLivelloChange(rowId, Number(e.target.value))}
            aria-label={`Livello compatibilità riga ${rowId}`}
          />
          <span className="pm-compat__slider-value">{livello}</span>
        </label>
      </div>

      {loading ? (
        <div className="pm-compat__loading">
          <div className="spinner spinner--sm" />
          <span>Aggiornamento cicli compatibili…</span>
        </div>
      ) : error ? (
        <p className="pm-compat__error">{error}</p>
      ) : compatibili.length === 0 ? (
        <p className="pm-compat__empty-msg">
          Nessun ciclo compatibile a questo livello. Abbassa lo slider per ampliare la ricerca.
        </p>
      ) : (
        <div className="pm-compat__list">
          {compatibili.map((item, i) => {
            const c = item.ciclo || {}
            const label = [
              c.codice_ciclo,
              c.ds_ciclo || c.ds_articolo,
              c.codice_stagione || c.ds_stagione,
            ]
              .filter(Boolean)
              .join(' · ')
            return (
              <details key={`${c.codice_ciclo}-${c.codice_articolo}-${i}`} className="pm-compat-card">
                <summary>
                  <CompatPct value={item.compatibilita} />
                  <span className="pm-compat-card__label" title={label}>
                    {label || 'Ciclo'}
                  </span>
                  <span className="pm-compat-card__keys">
                    {[c.codice_articolo, c.codice_linea, c.codice_composizione]
                      .filter(Boolean)
                      .join(' / ')}
                  </span>
                </summary>
                <div className="pm-compat-card__body">
                  <div className="pm-compat-card__block">
                    <h4>Differenze</h4>
                    <DiffList items={item.differenze} />
                  </div>
                  <div className="pm-compat-card__block">
                    <h4>Similarità</h4>
                    <SimiliList items={item.simili} />
                  </div>
                  {c.fasi?.length ? (
                    <div className="pm-compat-card__block">
                      <h4>Fasi candidato</h4>
                      <ol className="pm-compat-fasi">
                        {c.fasi.map((f, fi) => (
                          <li key={fi}>{f}</li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </div>
              </details>
            )
          })}
        </div>
      )}
    </div>
  )
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

  /** @type {[Record<string, {loading:boolean, error?:string, compatibili:any[], livello:number, soglia?:number}>, Function]} */
  const [compatByRow, setCompatByRow] = useState({})
  const [livelloByRow, setLivelloByRow] = useState({})
  /** Contatore per-riga: evita che una risposta stale sovrascriva uno slider più recente. */
  const rowReqRef = useRef({})

  const fetchCompatibili = useCallback(async (righe, livello) => {
    const ids = righe.map((r) => r.id)
    const tokens = {}
    for (const id of ids) {
      tokens[id] = (rowReqRef.current[id] || 0) + 1
      rowReqRef.current[id] = tokens[id]
    }

    setCompatByRow((prev) => {
      const next = { ...prev }
      for (const id of ids) {
        next[id] = {
          ...(next[id] || {}),
          loading: true,
          error: undefined,
          livello,
        }
      }
      return next
    })

    try {
      const res = await authFetch('/api/admin/prezzi-mancanti/cicli-compatibili', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ livello, righe }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Errore cicli compatibili')

      setCompatByRow((prev) => {
        const next = { ...prev }
        for (const id of ids) {
          if (rowReqRef.current[id] !== tokens[id]) continue
          const item = data.results?.[id]
          next[id] = {
            loading: false,
            ok: item?.ok !== false,
            error: item?.error || undefined,
            compatibili: item?.compatibili || [],
            livello: item?.livello ?? livello,
            soglia: item?.soglia ?? data.soglia,
          }
        }
        return next
      })
    } catch (err) {
      console.error(err)
      setCompatByRow((prev) => {
        const next = { ...prev }
        for (const id of ids) {
          if (rowReqRef.current[id] !== tokens[id]) continue
          next[id] = {
            ...(next[id] || {}),
            loading: false,
            error: err.message || 'Errore cicli compatibili',
            compatibili: next[id]?.compatibili || [],
            livello,
          }
        }
        return next
      })
    }
  }, [])

  const loadList = useCallback(() => {
    if (!dataDaApplied || !dataAApplied) return
    setLoading(true)
    setError('')
    setCompatByRow({})
    setLivelloByRow({})
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
        const nextRows = data.data || []
        setRows(nextRows)
        setPages(data.pages || 1)
        setTotal(data.total || 0)
        setRange({ da: data.data_da || '', a: data.data_a || '' })

        const livelli = {}
        const payload = nextRows.map((row, idx) => {
          const id = rowKey(row, idx)
          livelli[id] = DEFAULT_LIVELLO
          return cicloPayload(row, id)
        })
        setLivelloByRow(livelli)
        if (payload.length) {
          fetchCompatibili(payload, DEFAULT_LIVELLO)
        }
      })
      .catch((err) => {
        console.error(err)
        setError(err.message)
        setRows([])
        setTotal(0)
        setPages(1)
      })
      .finally(() => setLoading(false))
  }, [dataDaApplied, dataAApplied, page, fetchCompatibili])

  useEffect(() => {
    loadList()
  }, [loadList])

  const handleLivelloChange = (id, livello) => {
    setLivelloByRow((prev) => ({ ...prev, [id]: livello }))
    const idx = rows.findIndex((row, i) => rowKey(row, i) === id)
    if (idx < 0) return
    fetchCompatibili([cicloPayload(rows[idx], id)], livello)
  }

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
    setCompatByRow({})
    setLivelloByRow({})
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
              Sotto ogni riga compaiono i cicli compatibili (livello {DEFAULT_LIVELLO} di default);
              lo slider aggiorna solo quella riga.
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
                      {rows.map((row, idx) => {
                        const id = rowKey(row, idx)
                        const livello = livelloByRow[id] ?? DEFAULT_LIVELLO
                        return (
                          <React.Fragment key={id}>
                            <tr className="chats-table__row prezzi-mancanti-table__main">
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
                            <tr className="prezzi-mancanti-table__compat-row">
                              <td colSpan={COL_COUNT}>
                                <CicliCompatibiliPanel
                                  rowId={id}
                                  stato={compatByRow[id]}
                                  livello={livello}
                                  onLivelloChange={handleLivelloChange}
                                />
                              </td>
                            </tr>
                          </React.Fragment>
                        )
                      })}
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

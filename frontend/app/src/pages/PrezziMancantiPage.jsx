import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { authFetch } from '../utils/auth'
import { useAuth } from '../context/AuthContext'
import UserMenu from '../components/UserMenu'
import AdminNav from '../components/AdminNav'
import PrezziMancantiIcon from '../components/PrezziMancantiIcon'
import DateInput from '../components/DateInput'
import Pagination from '../components/Pagination'
import CicliCompatibiliResults from '../components/CicliCompatibiliResults'
import { LIVELLO_HINT } from '../components/cicliCompatibiliConstants'
import { printPrezziMancanti } from '../utils/printReports'

const PAGE_SIZE = 100
const DEFAULT_LIVELLO = 4

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

/** Nome anagrafica + descrizione bolla + codice (se diverso dal nome). */
function formatArticoloDisplay(row) {
  const codice = String(row.codice_articolo || '').trim()
  const nome = String(row.nome_articolo || '').trim()
  const desc = String(row.ds_articolo || row.articolo || '').trim()
  const primary = nome || codice
  const parts = []
  if (primary) parts.push(primary)
  if (desc && desc.toLocaleUpperCase('it-IT') !== primary.toLocaleUpperCase('it-IT')) {
    parts.push(desc)
  }
  let label = parts.join(' — ')
  if (
    codice &&
    nome &&
    codice.toLocaleUpperCase('it-IT') !== nome.toLocaleUpperCase('it-IT')
  ) {
    label = label ? `${label} (${codice})` : codice
  }
  return label || null
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

function clienteGroupKey(row) {
  return String(row.cliente_codice || row.codice_cliente || row.cliente || '').trim() || '—'
}

function clienteGroupLabel(row) {
  const code = String(row.cliente_codice || '').trim()
  const name = String(row.cliente_nome || '').trim()
  if (code && name) return `${code} — ${name}`
  return row.cliente || code || name || 'Cliente sconosciuto'
}

/** Etichetta corta per le chip (nome, o codice). */
function clienteChipLabel(row) {
  const name = String(row.cliente_nome || '').trim()
  const code = String(row.cliente_codice || '').trim()
  if (name) return name
  return code || row.cliente || '—'
}

/** Raggruppa le righe consecutive per cliente (ordine già per cliente lato API). */
function groupRowsByCliente(rows) {
  const groups = []
  for (let idx = 0; idx < rows.length; idx += 1) {
    const row = rows[idx]
    const key = clienteGroupKey(row)
    const last = groups[groups.length - 1]
    if (last && last.key === key) {
      last.items.push({ row, idx })
    } else {
      groups.push({
        key,
        label: clienteGroupLabel(row),
        chipLabel: clienteChipLabel(row),
        items: [{ row, idx }],
      })
    }
  }
  return groups
}

function CicliCompatibiliPanel({ rowId, stato, livello, onLivelloChange }) {
  return (
    <CicliCompatibiliResults
      loading={!stato || stato.loading}
      error={stato?.error}
      compatibili={stato?.compatibili || []}
      livello={livello}
      soglia={stato?.soglia}
      onLivelloChange={(next) => onLivelloChange(rowId, next)}
    />
  )
}

export default function PrezziMancantiPage() {
  const { user } = useAuth()
  const isCicliOnly = user?.role === 'cicli'
  const [dataDaFilter, setDataDaFilter] = useState(monthStartISO())
  const [dataAFilter, setDataAFilter] = useState(todayISO())
  const [dataDaApplied, setDataDaApplied] = useState('')
  const [dataAApplied, setDataAApplied] = useState('')
  /** Default TRUE: solo cicli compatibili con offerta/prezzo associato. */
  const [prezziPresenti, setPrezziPresenti] = useState(true)
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
  /** Visibilità gruppi cliente (solo UI): key → true/false. Default true. */
  const [clienteVisible, setClienteVisible] = useState({})
  /** Contatore per-riga: evita che una risposta stale sovrascriva uno slider più recente. */
  const rowReqRef = useRef({})
  const prezziPresentiRef = useRef(prezziPresenti)
  prezziPresentiRef.current = prezziPresenti

  const fetchCompatibili = useCallback(async (righe, livello, prezziPresentiOpt) => {
    const prezzi = prezziPresentiOpt ?? prezziPresentiRef.current
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
        body: JSON.stringify({
          livello,
          prezzi_presenti: prezzi !== false,
          righe,
        }),
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
          fetchCompatibili(payload, DEFAULT_LIVELLO, prezziPresentiRef.current)
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
    fetchCompatibili([cicloPayload(rows[idx], id)], livello, prezziPresenti)
  }

  const handlePrezziPresentiChange = (checked) => {
    setPrezziPresenti(checked)
    if (!searched || !rows.length) return
    // Ricalcola tutte le righe della pagina col nuovo filtro, rispettando il livello corrente.
    const byLivello = new Map()
    rows.forEach((row, idx) => {
      const id = rowKey(row, idx)
      const livello = livelloByRow[id] ?? DEFAULT_LIVELLO
      if (!byLivello.has(livello)) byLivello.set(livello, [])
      byLivello.get(livello).push(cicloPayload(row, id))
    })
    for (const [livello, payload] of byLivello) {
      fetchCompatibili(payload, livello, checked)
    }
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
    setPrezziPresenti(true)
    setSearched(false)
    setRows([])
    setTotal(0)
    setPages(1)
    setPage(1)
    setError('')
    setRange({ da: '', a: '' })
    setCompatByRow({})
    setLivelloByRow({})
    setClienteVisible({})
  }

  const clienteGroups = useMemo(() => groupRowsByCliente(rows), [rows])

  useEffect(() => {
    setClienteVisible((prev) => {
      const next = {}
      for (const g of clienteGroups) {
        next[g.key] = prev[g.key] !== false
      }
      const prevKeys = Object.keys(prev)
      const nextKeys = Object.keys(next)
      if (
        prevKeys.length === nextKeys.length &&
        nextKeys.every((k) => k in prev && prev[k] === next[k])
      ) {
        return prev
      }
      return next
    })
  }, [clienteGroups])

  const visibleClienteGroups = useMemo(
    () => clienteGroups.filter((g) => clienteVisible[g.key] !== false),
    [clienteGroups, clienteVisible],
  )

  const toggleClienteVisible = (key) => {
    setClienteVisible((prev) => ({
      ...prev,
      [key]: prev[key] === false,
    }))
  }

  const setAllClientiVisible = (visible) => {
    setClienteVisible((prev) => {
      const next = { ...prev }
      for (const g of clienteGroups) next[g.key] = visible
      return next
    })
  }

  return (
    <div className="app-container">
      <div className="app-sticky-top">
        <header className="app-header">
          <div className="app-title-group">
            <a href={isCicliOnly ? '/cicli' : '/'} className="app-logo-link">
              <img src="/logo.webp" alt="Intex" className="app-logo" />
            </a>
          </div>
          <div className="app-header__actions">
            <UserMenu />
            {!isCicliOnly && <AdminNav />}
          </div>
        </header>

        <nav className="nav-primary" aria-label="Navigazione principale">
          {isCicliOnly ? (
            <>
              <a href="/cicli" className="nav-tab">
                🧵 Cicli
              </a>
              <a href="/cicli?mode=upload" className="nav-tab">
                📄 Upload bolla
              </a>
              <a href="/prezzi-mancanti" className="nav-tab is-active" aria-current="page">
                <PrezziMancantiIcon /> Prezzi mancanti
              </a>
            </>
          ) : (
            <>
              <a href="/?tab=bolle" className="nav-tab">
                📦 Bolle / DDT
              </a>
              <a href="/?tab=fatture" className="nav-tab">
                🧾 Fatture
              </a>
              <a href="/?tab=offerte" className="nav-tab">
                📋 Ordini / Cartellino
              </a>
              <a href="/?tab=discrepanze" className="nav-tab">
                ⚖️ Auditing Confronto
              </a>
              <a href="/?tab=assistente" className="nav-tab">
                🤖 Assistente DDT
              </a>
              <a href="/cicli" className="nav-tab">
                🧵 Cicli
              </a>
              <a href="/analisi" className="nav-tab">
                📊 Analisi
              </a>
              <a href="/prezzi-mancanti" className="nav-tab is-active" aria-current="page">
                <PrezziMancantiIcon /> Prezzi mancanti
              </a>
            </>
          )}
        </nav>
      </div>

      <div className="logs-page prezzi-mancanti-page">
        <div className="panel logs-list-panel">
          <div className="pm-sticky-controls">
            <div className="pm-sticky-controls__bar">
              <div className="pm-sticky-controls__title">
                <strong>
                  Prezzi mancanti
                  {searched ? ` (${total})` : ''}
                </strong>
                {range.da && range.a ? (
                  <span className="pm-sticky-controls__period">
                    {formatIt(range.da)} – {formatIt(range.a)}
                  </span>
                ) : null}
              </div>

              <form className="pm-filters pm-filters--compact" onSubmit={handleSearch}>
                <label className="pm-field-inline">
                  <span>Da</span>
                  <DateInput
                    name="data_da"
                    value={dataDaFilter}
                    onChange={(e) => setDataDaFilter(e.target.value)}
                    placeholder="Data da…"
                  />
                </label>
                <label className="pm-field-inline">
                  <span>A</span>
                  <DateInput
                    name="data_a"
                    value={dataAFilter}
                    onChange={(e) => setDataAFilter(e.target.value)}
                    placeholder="Data a…"
                  />
                </label>
                <label
                  className="pm-field-inline pm-prezzi-presenti--compact"
                  title="Se attivo, i cicli compatibili devono avere un'offerta con prezzo > 0"
                >
                  <input
                    type="checkbox"
                    name="prezzi_presenti"
                    checked={prezziPresenti}
                    onChange={(e) => handlePrezziPresentiChange(e.target.checked)}
                  />
                  <span>Solo con prezzo</span>
                </label>
                <button type="submit" className="btn btn--primary btn--sm">
                  Cerca
                </button>
                <button type="button" className="btn btn--sm" onClick={handleReset}>
                  Reset
                </button>
                {searched && rows.length > 0 ? (
                  <button
                    type="button"
                    className="btn btn--sm"
                    disabled={loading}
                    title="Stampa i clienti visibili della pagina corrente con i cicli compatibili espansi"
                    onClick={() => {
                      try {
                        const items = visibleClienteGroups.flatMap((g) => g.items)
                        printPrezziMancanti({
                          rows: items.map(({ row }) => row),
                          compatByRow,
                          livelloByRow,
                          defaultLivello: DEFAULT_LIVELLO,
                          page,
                          pages,
                          total,
                          range,
                          prezziPresenti,
                          rowKeyFn: (row, i) => rowKey(row, items[i].idx),
                          livelloHint: LIVELLO_HINT,
                        })
                      } catch (err) {
                        console.error(err)
                        window.alert(err.message || 'Impossibile aprire la stampa.')
                      }
                    }}
                  >
                    Stampa
                  </button>
                ) : null}
              </form>
            </div>

            {!loading && searched && clienteGroups.length > 0 ? (
              <div className="pm-cliente-filter" role="group" aria-label="Filtra clienti nei risultati">
                <div className="pm-cliente-filter__chips">
                  <span className="pm-cliente-filter__label">Clienti</span>
                  <button
                    type="button"
                    className="pm-cliente-filter__bulk"
                    onClick={() => setAllClientiVisible(true)}
                  >
                    Tutti
                  </button>
                  <button
                    type="button"
                    className="pm-cliente-filter__bulk"
                    onClick={() => setAllClientiVisible(false)}
                  >
                    Nessuno
                  </button>
                  <span className="pm-cliente-filter__meta">
                    {visibleClienteGroups.length}/{clienteGroups.length}
                  </span>
                  {clienteGroups.map((group) => {
                    const checked = clienteVisible[group.key] !== false
                    return (
                      <label
                        key={group.key}
                        className={`pm-cliente-chip${checked ? '' : ' is-off'}`}
                        title={group.label}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleClienteVisible(group.key)}
                        />
                        <span className="pm-cliente-chip__name">{group.chipLabel}</span>
                        <span className="pm-cliente-chip__count">{group.items.length}</span>
                      </label>
                    )
                  })}
                </div>
              </div>
            ) : null}
          </div>

          <div className="panel__body panel__body--compact pm-results-body">
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
            ) : visibleClienteGroups.length === 0 ? (
              <p className="users-empty">
                Nessun cliente selezionato. Usa le spunte sopra per mostrare i risultati.
              </p>
            ) : (
              <>
                <div className="pm-cliente-groups">
                  {visibleClienteGroups.map((group) => (
                    <section key={group.key} className="pm-cliente-group">
                      <header className="pm-cliente-group__head">
                        <div className="pm-cliente-group__title">
                          <span className="pm-cliente-group__badge">Cliente</span>
                          <h3 className="pm-cliente-group__name" title={group.label}>
                            {group.label}
                          </h3>
                        </div>
                        <span className="pm-cliente-group__count">
                          {group.items.length}{' '}
                          {group.items.length === 1 ? 'riga' : 'righe'}
                        </span>
                      </header>
                      <div className="pm-rows pm-rows--grouped">
                        {group.items.map(({ row, idx }) => {
                          const id = rowKey(row, idx)
                          const livello = livelloByRow[id] ?? DEFAULT_LIVELLO
                          const metaFields = [
                            { label: 'Articolo', value: formatArticoloDisplay(row) },
                            { label: 'Linea', value: row.linea },
                            { label: 'Stag. listino', value: row.stagione_listino },
                            { label: 'Stag. prod.', value: row.stagione_produzione },
                            { label: 'Composizione', value: row.composizione },
                            { label: 'Ns. disposiz.', value: row.ns_disposiz },
                            { label: 'Ciclo lavoro', value: row.ciclo_lavoro },
                          ].filter((f) => f.value != null && String(f.value).trim() !== '')
                          return (
                            <article key={id} className="pm-row">
                              <div className="pm-row__head">
                                <div className="pm-row__primary">
                                  <div className="pm-row__identity">
                                    <span className="pm-row__ddt pm-row__ddt--primary">
                                      {[
                                        row.ns_ddt ? `DDT ${row.ns_ddt}` : null,
                                        row.data_ddt || null,
                                        row.tipo || null,
                                      ]
                                        .filter(Boolean)
                                        .join(' · ') || '—'}
                                    </span>
                                  </div>
                                  <div className="pm-row__ciclo-block">
                                    <em>Ciclo</em>
                                    <strong title={row.ciclo || ''}>{row.ciclo || '—'}</strong>
                                  </div>
                                  <div className="pm-row__qty">
                                    <span>
                                      <em>Capi</em> {formatQty(row.capi_sped)}
                                    </span>
                                    <span>
                                      <em>Kg</em> {formatQty(row.kg_sped)}
                                    </span>
                                  </div>
                                </div>
                                {metaFields.length ? (
                                  <div className="pm-row__meta">
                                    {metaFields.map((f) => (
                                      <span key={f.label} className="pm-row__meta-item">
                                        <em>{f.label}</em>
                                        <strong title={String(f.value)}>{f.value}</strong>
                                      </span>
                                    ))}
                                  </div>
                                ) : null}
                              </div>
                              <div className="pm-row__compat">
                                <CicliCompatibiliPanel
                                  rowId={id}
                                  stato={compatByRow[id]}
                                  livello={livello}
                                  onLivelloChange={handleLivelloChange}
                                />
                              </div>
                            </article>
                          )
                        })}
                      </div>
                    </section>
                  ))}
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

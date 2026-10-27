import React, { useCallback, useEffect, useState } from 'react'
import CustomerAutocomplete from '../components/CustomerAutocomplete'
import SeasonAutocomplete from '../components/SeasonAutocomplete'
import FilterSuggest from '../components/FilterSuggest'
import FasiChipInput from '../components/FasiChipInput'
import Pagination from '../components/Pagination'
import LoadingOverlay from '../components/LoadingOverlay'
import BollaUploadPanel from '../components/BollaUploadPanel'
import { authFetch } from '../utils/auth'

const PAGE_SIZE = 50

const MODES = [
  { id: 'ricerca', label: 'Ricerca' },
  { id: 'upload', label: 'Upload bolla' },
]

/** Dizionario fisso reparti (valore inviato all'API; Tutti = nessun filtro). */
const REPARTI_OPTIONS = [
  { value: 'TUTTI', label: 'Tutti' },
  { value: 'TINTO', label: 'TINTO' },
  { value: 'DENIM', label: 'DENIM' },
  { value: 'INTEX', label: 'INTEX' },
  { value: 'PROTOTIPI', label: 'PROTOTIPI' },
  { value: 'EFFETTI SPECIALI', label: 'EFFETTI SPECIALI' },
]

function readModeFromUrl() {
  const mode = new URLSearchParams(window.location.search).get('mode')
  return MODES.some((m) => m.id === mode) ? mode : 'ricerca'
}

const EMPTY_FILTERS = {
  q: '',
  codice_cliente: '',
  stagione: '',
  codice_ciclo: '',
  codice_univoco: '',
  articolo: '',
  composizione: '',
  descrizione: '',
  reparto: 'TUTTI',
  fasi: [],
  fasi_mode: 'all',
  fasi_note_storico: false,
  colore: '',
  tessuto: '',
  commessa: '',
  modello: '',
  articolo_fiscale: '',
  data_bolla_da: '',
  data_bolla_a: '',
  vista: 'cicli',
}

function cicloKey(item) {
  return [
    item.codice_cliente,
    item.codice_articolo,
    item.codice_ciclo,
    item.codice_linea,
    item.codice_stagione,
    item.codice_composizione,
  ].join('|')
}

function formatDateIso(iso) {
  if (!iso) return '—'
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return iso
  return `${m[3]}/${m[2]}/${m[1]}`
}

function buildQueryParams(nextFilters, nextPage) {
  const params = new URLSearchParams()
  if (nextFilters.q) params.append('q', nextFilters.q)
  if (nextFilters.codice_cliente) params.append('codice_cliente', nextFilters.codice_cliente)
  if (nextFilters.stagione) params.append('stagione', nextFilters.stagione)
  if (nextFilters.codice_ciclo) params.append('codice_ciclo', nextFilters.codice_ciclo)
  if (nextFilters.codice_univoco) params.append('codice_univoco', nextFilters.codice_univoco)
  if (nextFilters.articolo) params.append('articolo', nextFilters.articolo)
  if (nextFilters.composizione) params.append('composizione', nextFilters.composizione)
  if (nextFilters.descrizione) params.append('descrizione', nextFilters.descrizione)
  if (nextFilters.reparto && nextFilters.reparto !== 'TUTTI') {
    params.append('reparto', nextFilters.reparto)
  }
  ;(nextFilters.fasi || []).forEach((f) => params.append('fasi', f))
  if (nextFilters.fasi_mode) params.append('fasi_mode', nextFilters.fasi_mode)
  if (nextFilters.fasi_note_storico) params.append('fasi_note_storico', '1')
  if (nextFilters.colore) params.append('colore', nextFilters.colore)
  if (nextFilters.tessuto) params.append('tessuto', nextFilters.tessuto)
  if (nextFilters.commessa) params.append('commessa', nextFilters.commessa)
  if (nextFilters.modello) params.append('modello', nextFilters.modello)
  if (nextFilters.articolo_fiscale) params.append('articolo_fiscale', nextFilters.articolo_fiscale)
  if (nextFilters.data_bolla_da) params.append('data_bolla_da', nextFilters.data_bolla_da)
  if (nextFilters.data_bolla_a) params.append('data_bolla_a', nextFilters.data_bolla_a)
  if (nextFilters.vista) params.append('vista', nextFilters.vista)
  params.append('page', String(nextPage))
  params.append('limit', String(PAGE_SIZE))
  return params
}

export default function CicliPage({ mode: modeProp, onModeChange } = {}) {
  const [modeState, setModeState] = useState(readModeFromUrl)
  const mode = modeProp ?? modeState
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS })
  const [appliedFilters, setAppliedFilters] = useState({ ...EMPTY_FILTERS })
  const [faseInput, setFaseInput] = useState('')
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [fasiEspanse, setFasiEspanse] = useState({})
  const [storicoDisponibile, setStoricoDisponibile] = useState(null)
  const [expandedKey, setExpandedKey] = useState(null)
  const [expandedKind, setExpandedKind] = useState(null) // 'fasi' | 'utilizzi'
  const [fasiByKey, setFasiByKey] = useState({})
  const [utilizziByKey, setUtilizziByKey] = useState({})
  const [detailLoading, setDetailLoading] = useState(null)

  const fetchCicli = useCallback((nextFilters, nextPage = 1) => {
    setLoading(true)
    const params = buildQueryParams(nextFilters, nextPage)

    authFetch(`/api/cicli?${params.toString()}`)
      .then((res) => res.json())
      .then((resData) => {
        setData(resData.data || [])
        setTotal(resData.total ?? 0)
        setPage(resData.page ?? nextPage)
        setPages(resData.pages ?? 1)
        setFasiEspanse(resData.fasi_espanse || {})
        setStoricoDisponibile(resData.storico_disponibile || null)
        setExpandedKey(null)
        setExpandedKind(null)
      })
      .catch((err) => {
        console.error('Error fetching cicli:', err)
        setData([])
        setTotal(0)
        setPages(1)
        setFasiEspanse({})
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchCicli(EMPTY_FILTERS, 1)
  }, [fetchCicli])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFilters((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleFasiChange = (fasi) => {
    setFilters((prev) => ({ ...prev, fasi }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const next = { ...filters }
    const pending = faseInput.trim()
    if (pending && !next.fasi.some((f) => f.toLowerCase() === pending.toLowerCase())) {
      next.fasi = [...next.fasi, pending]
      setFaseInput('')
      setFilters(next)
    }
    setAppliedFilters(next)
    fetchCicli(next, 1)
  }

  const handleReset = () => {
    setFilters({ ...EMPTY_FILTERS })
    setAppliedFilters({ ...EMPTY_FILTERS })
    setFaseInput('')
    fetchCicli(EMPTY_FILTERS, 1)
  }

  const handlePageChange = (nextPage) => {
    fetchCicli(appliedFilters, nextPage)
  }

  const setMode = (next) => {
    if (onModeChange) {
      onModeChange(next)
    } else {
      setModeState(next)
      const url = new URL(window.location.href)
      if (next === 'ricerca') url.searchParams.delete('mode')
      else url.searchParams.set('mode', next)
      window.history.replaceState(window.history.state, '', url)
    }
  }

  const openInRicerca = (patch) => {
    const next = { ...EMPTY_FILTERS, ...patch }
    setFilters(next)
    setAppliedFilters(next)
    setFaseInput('')
    fetchCicli(next, 1)
    setMode('ricerca')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const setVista = (vista) => {
    const next = { ...filters, vista }
    setFilters(next)
    setAppliedFilters(next)
    fetchCicli(next, 1)
  }

  const toggleExpand = (item, kind) => {
    const key = cicloKey(item)
    if (expandedKey === key && expandedKind === kind) {
      setExpandedKey(null)
      setExpandedKind(null)
      return
    }
    setExpandedKey(key)
    setExpandedKind(kind)

    if (kind === 'fasi') {
      if (fasiByKey[key]) return
      setDetailLoading(key)
      const params = new URLSearchParams({
        codice_cliente: item.codice_cliente,
        codice_articolo: item.codice_articolo,
        codice_ciclo: item.codice_ciclo,
        codice_linea: item.codice_linea,
        codice_stagione: item.codice_stagione,
        codice_composizione: item.codice_composizione,
      })
      authFetch(`/api/cicli/fasi?${params.toString()}`)
        .then((res) => res.json())
        .then((resData) => {
          setFasiByKey((prev) => ({ ...prev, [key]: resData.data || [] }))
        })
        .catch((err) => {
          console.error('Error fetching fasi:', err)
          setFasiByKey((prev) => ({ ...prev, [key]: [] }))
        })
        .finally(() => setDetailLoading(null))
      return
    }

    if (kind === 'utilizzi') {
      if (utilizziByKey[key]) return
      setDetailLoading(key)
      const params = new URLSearchParams({
        codice_cliente: item.codice_cliente,
        codice_articolo: item.codice_articolo,
        codice_ciclo: item.codice_ciclo,
        codice_linea: item.codice_linea,
        codice_stagione: item.codice_stagione,
        codice_composizione: item.codice_composizione,
      })
      if (appliedFilters.colore) params.append('colore', appliedFilters.colore)
      if (appliedFilters.tessuto) params.append('tessuto', appliedFilters.tessuto)
      if (appliedFilters.commessa) params.append('commessa', appliedFilters.commessa)
      if (appliedFilters.modello) params.append('modello', appliedFilters.modello)
      if (appliedFilters.articolo_fiscale) {
        params.append('articolo_fiscale', appliedFilters.articolo_fiscale)
      }
      if (appliedFilters.data_bolla_da) params.append('data_bolla_da', appliedFilters.data_bolla_da)
      if (appliedFilters.data_bolla_a) params.append('data_bolla_a', appliedFilters.data_bolla_a)
      authFetch(`/api/cicli/utilizzi?${params.toString()}`)
        .then((res) => res.json())
        .then((resData) => {
          setUtilizziByKey((prev) => ({ ...prev, [key]: resData.data || [] }))
        })
        .catch((err) => {
          console.error('Error fetching utilizzi:', err)
          setUtilizziByKey((prev) => ({ ...prev, [key]: [] }))
        })
        .finally(() => setDetailLoading(null))
    }
  }

  const isUtilizziVista = appliedFilters.vista === 'utilizzi'
  const espanseEntries = Object.entries(fasiEspanse || {})

  return (
    <>
      <div className="cicli-mode-bar">
        <h2 className="cicli-mode-bar__title">Cicli di lavorazione</h2>
        <div className="cicli-mode-switch" role="tablist" aria-label="Modalità pagina cicli">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={mode === m.id}
              className={`cicli-mode-switch__btn${mode === m.id ? ' cicli-mode-switch__btn--active' : ''}`}
              onClick={() => setMode(m.id)}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div hidden={mode !== 'upload'}>
        <BollaUploadPanel onOpenInRicerca={openInRicerca} />
      </div>

      <div hidden={mode !== 'ricerca'}>
      {loading && mode === 'ricerca' && <LoadingOverlay />}
      <div className="panel">
        <div className="panel__head">Ricerca cicli di lavorazione</div>
        <div className="panel__body">
          <form onSubmit={handleSubmit} className="filters-form">
            <div className="filter-section-title">Ricerca globale</div>
            <div className="field field--full" style={{ marginBottom: '1.25rem' }}>
              <label htmlFor="filtro-q">Cerca ovunque</label>
              <input
                id="filtro-q"
                type="text"
                name="q"
                value={filters.q}
                onChange={handleChange}
                placeholder="Testo libero su ciclo, fasi, commessa, colore, modello…"
                autoComplete="off"
              />
              <div className="field-hint" style={{ marginTop: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Cerca in tutti i campi insieme (min. 2 caratteri). I filtri sotto restano attivi e restringono ulteriormente.
              </div>
            </div>

            <div className="filter-section-title">Ciclo</div>
            <div className="filters-grid">
              <div className="field">
                <label>Cliente</label>
                <CustomerAutocomplete
                  name="codice_cliente"
                  value={filters.codice_cliente}
                  onChange={handleChange}
                  placeholder="Cerca per nome o codice..."
                  allowClear
                  endpoint="/api/cicli/clienti"
                />
              </div>
              <div className="field">
                <label>Stagione</label>
                <SeasonAutocomplete
                  name="stagione"
                  value={filters.stagione}
                  onChange={handleChange}
                  placeholder="Cerca stagione..."
                  allowClear
                />
              </div>
              <div className="field">
                <label>Codice ciclo</label>
                <FilterSuggest
                  name="codice_ciclo"
                  value={filters.codice_ciclo}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/codice_ciclo"
                  placeholder="Es. T139..."
                  minChars={2}
                  params={{ codice_cliente: filters.codice_cliente }}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Cod. Univoco</label>
                <FilterSuggest
                  name="codice_univoco"
                  value={filters.codice_univoco}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/codice_univoco"
                  placeholder="Es. 41434..."
                  minChars={1}
                  params={{ codice_cliente: filters.codice_cliente }}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Articolo cliente</label>
                <FilterSuggest
                  name="articolo"
                  value={filters.articolo}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/articolo"
                  placeholder="Codice o descrizione articolo cliente..."
                  minChars={2}
                  params={{ codice_cliente: filters.codice_cliente }}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Composizione</label>
                <input
                  type="text"
                  name="composizione"
                  value={filters.composizione}
                  onChange={handleChange}
                  placeholder="Es. cotone elastan..."
                />
              </div>
              <div className="field">
                <label>Descrizione ciclo</label>
                <input
                  type="text"
                  name="descrizione"
                  value={filters.descrizione}
                  onChange={handleChange}
                  placeholder="Match letterale su descrizione..."
                />
              </div>
              <div className="field">
                <label htmlFor="filtro-reparto">Reparto</label>
                <select
                  id="filtro-reparto"
                  name="reparto"
                  value={filters.reparto || 'TUTTI'}
                  onChange={handleChange}
                  required
                >
                  {REPARTI_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="field field--full" style={{ marginBottom: '1.25rem' }}>
              <label>Fasi / lavorazioni</label>
              <FasiChipInput
                chips={filters.fasi}
                onChange={handleFasiChange}
                draft={faseInput}
                onDraftChange={setFaseInput}
              />
              <div className="field-row-inline" style={{ marginTop: '0.5rem' }}>
                <label className="checkbox-inline">
                  <input
                    type="radio"
                    name="fasi_mode"
                    value="all"
                    checked={filters.fasi_mode === 'all'}
                    onChange={handleChange}
                  />
                  Tutte le parole
                </label>
                <label className="checkbox-inline">
                  <input
                    type="radio"
                    name="fasi_mode"
                    value="any"
                    checked={filters.fasi_mode === 'any'}
                    onChange={handleChange}
                  />
                  Almeno una
                </label>
                <label className="checkbox-inline">
                  <input
                    type="checkbox"
                    name="fasi_note_storico"
                    checked={!!filters.fasi_note_storico}
                    onChange={handleChange}
                  />
                  Anche note disposizioni
                </label>
              </div>
            </div>

            <div className="filter-section-title">
              Storico disposizioni
              {storicoDisponibile?.da || storicoDisponibile?.a ? (
                <span className="text-secondary" style={{ fontWeight: 400, marginLeft: '0.5rem' }}>
                  (disponibile
                  {storicoDisponibile.da ? ` dal ${formatDateIso(storicoDisponibile.da)}` : ''}
                  {storicoDisponibile.a ? ` al ${formatDateIso(storicoDisponibile.a)}` : ''})
                </span>
              ) : null}
            </div>
            <div className="filters-grid">
              <div className="field">
                <label>Commessa</label>
                <FilterSuggest
                  name="commessa"
                  value={filters.commessa}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/commessa"
                  placeholder="Rif. disp. cliente..."
                  minChars={3}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Modello</label>
                <FilterSuggest
                  name="modello"
                  value={filters.modello}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/modello"
                  placeholder="Nome capo codice cliente..."
                  minChars={2}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Colore</label>
                <FilterSuggest
                  name="colore"
                  value={filters.colore}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/colore"
                  placeholder="Codice o descrizione colore..."
                  minChars={2}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Tessuto / Descrizione articolo</label>
                <FilterSuggest
                  name="tessuto"
                  value={filters.tessuto}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/tessuto"
                  placeholder="Testo in descrizione/articolo o codice qualità..."
                  minChars={2}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Articolo fiscale</label>
                <FilterSuggest
                  name="articolo_fiscale"
                  value={filters.articolo_fiscale}
                  onChange={handleChange}
                  endpoint="/api/cicli/suggest/articolo_fiscale"
                  placeholder="Es. CAPI..."
                  minChars={1}
                  allowClear
                />
              </div>
              <div className="field">
                <label>Data bolla da</label>
                <input
                  type="date"
                  name="data_bolla_da"
                  value={filters.data_bolla_da}
                  onChange={handleChange}
                />
              </div>
              <div className="field">
                <label>Data bolla a</label>
                <input
                  type="date"
                  name="data_bolla_a"
                  value={filters.data_bolla_a}
                  onChange={handleChange}
                />
              </div>
            </div>

            <div className="actions-bar">
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button type="submit" className="btn btn--primary">
                  Cerca
                </button>
                <button type="button" onClick={handleReset} className="btn">
                  Azzera filtri
                </button>
              </div>
              <div className="vista-toggle">
                <button
                  type="button"
                  className={`btn btn--sm ${!isUtilizziVista ? 'btn--primary' : ''}`}
                  onClick={() => setVista('cicli')}
                >
                  Vista cicli
                </button>
                <button
                  type="button"
                  className={`btn btn--sm ${isUtilizziVista ? 'btn--primary' : ''}`}
                  onClick={() => setVista('utilizzi')}
                >
                  Vista utilizzi
                </button>
              </div>
            </div>
          </form>

          {espanseEntries.length > 0 && (
            <div className="fasi-espanse" style={{ marginTop: '1rem' }}>
              <div className="text-secondary" style={{ marginBottom: '0.35rem' }}>
                Varianti usate nella ricerca fasi:
              </div>
              {espanseEntries.map(([kw, variants]) => (
                <div key={kw} style={{ marginBottom: '0.25rem' }}>
                  <strong>{kw}</strong>
                  <span className="text-secondary"> → {(variants || []).slice(0, 12).join(', ')}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panel__head">
          <span>
            {isUtilizziVista ? 'Utilizzi storico' : 'Risultati cicli'}
            {total ? ` (${total})` : ''}
          </span>
        </div>
        <div className="panel__body">
          {data.length === 0 && !loading ? (
            <div className="empty-state">
              <div className="empty-state-icon">🔎</div>
              <h3>Nessun risultato</h3>
              <p>Prova a modificare i filtri di ricerca.</p>
            </div>
          ) : isUtilizziVista ? (
            <>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Data bolla</th>
                      <th>N. bolla</th>
                      <th>Ciclo</th>
                      <th>Cliente</th>
                      <th>Commessa</th>
                      <th>Modello</th>
                      <th>Descrizione / Articolo</th>
                      <th>Colore</th>
                      <th>Tessuto</th>
                      <th>Art. fiscale</th>
                      <th>Capi / Kg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, idx) => (
                      <tr
                        key={`${item.anno_disposizione}-${item.nr_disposizione}-${item.riga_disposizione}-${idx}`}
                        className={`cicli-row${idx % 2 === 1 ? ' cicli-row--alt' : ''}`}
                      >
                        <td>{item.data_bolla || '—'}</td>
                        <td>{item.nr_bolla || '—'}</td>
                        <td>
                          <strong>{item.codice_ciclo}</strong>
                          {item.codice_ciclo_cli ? (
                            <div className="text-secondary">{item.codice_ciclo_cli}</div>
                          ) : null}
                        </td>
                        <td>
                          {item.ragione_sociale || '—'}{' '}
                          <span className="text-secondary">({item.codice_cliente})</span>
                        </td>
                        <td>{item.commessa || '—'}</td>
                        <td>{item.modello || '—'}</td>
                        <td>{item.ds_articolo || '—'}</td>
                        <td>
                          {item.ds_colore || item.cd_colore || '—'}
                          {item.ds_colore && item.cd_colore ? (
                            <div className="text-secondary">{item.cd_colore}</div>
                          ) : null}
                        </td>
                        <td>{item.tessuto || '—'}</td>
                        <td>{item.articolo_fiscale || '—'}</td>
                        <td>
                          {item.capi_caricati ?? '—'} / {item.kg_caricati ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={page}
                pages={pages}
                total={total}
                onPageChange={handlePageChange}
                label="Utilizzi"
              />
            </>
          ) : (
            <>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Inserito il</th>
                      <th>Ultimo utilizzo</th>
                      <th>Ciclo</th>
                      <th>Descrizione</th>
                      <th>Cliente</th>
                      <th>Articolo</th>
                      <th>Stagione</th>
                      <th>Composizione</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((item, idx) => {
                      const key = cicloKey(item)
                      const isFasiOpen = expandedKey === key && expandedKind === 'fasi'
                      const isUtilizziOpen = expandedKey === key && expandedKind === 'utilizzi'
                      const isSelected = isFasiOpen || isUtilizziOpen
                      const fasi = fasiByKey[key] || []
                      const utilizzi = utilizziByKey[key] || []
                      const rowClass = [
                        'cicli-row',
                        idx % 2 === 1 ? 'cicli-row--alt' : '',
                        isSelected ? 'cicli-row--selected' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')
                      return (
                        <React.Fragment key={key}>
                          <tr className={rowClass}>
                            <td>{formatDateIso(item.data_ins)}</td>
                            <td>
                              {formatDateIso(item.ultima_bolla)}
                              {item.n_righe_storico ? (
                                <div className="text-secondary">{item.n_righe_storico} righe</div>
                              ) : null}
                            </td>
                            <td>
                              <strong>{item.codice_ciclo}</strong>
                              {item.codice_ciclo_cli ? (
                                <div className="text-secondary">{item.codice_ciclo_cli}</div>
                              ) : null}
                              {(item.match_fasi || []).length > 0 ? (
                                <div className="match-badges">
                                  {item.match_fasi.map((m) => (
                                    <span key={m} className="ddt-badge">
                                      {m}
                                    </span>
                                  ))}
                                </div>
                              ) : null}
                            </td>
                            <td>{item.ds_ciclo || '—'}</td>
                            <td>
                              {item.ragione_sociale || '—'}{' '}
                              <span className="text-secondary">({item.codice_cliente})</span>
                            </td>
                            <td>
                              {item.ds_articolo || item.codice_articolo}
                              {item.ds_articolo ? (
                                <div className="text-secondary">{item.codice_articolo}</div>
                              ) : null}
                            </td>
                            <td>{item.ds_stagione || item.codice_stagione || '—'}</td>
                            <td>{item.ds_composizione || item.codice_composizione || '—'}</td>
                            <td>
                              <span className="table-link" onClick={() => toggleExpand(item, 'fasi')}>
                                {isFasiOpen ? 'Nascondi fasi' : 'Fasi'}
                              </span>
                              {' · '}
                              <span
                                className="table-link"
                                onClick={() => toggleExpand(item, 'utilizzi')}
                              >
                                {isUtilizziOpen ? 'Nascondi utilizzi' : 'Utilizzi'}
                              </span>
                            </td>
                          </tr>
                          {isFasiOpen && (
                            <tr className="cicli-row cicli-row--detail cicli-row--selected">
                              <td colSpan={9}>
                                {detailLoading === key ? (
                                  <div className="text-secondary">Caricamento fasi…</div>
                                ) : fasi.length === 0 ? (
                                  <div className="text-secondary">Nessuna fase per questo ciclo.</div>
                                ) : (
                                  <table className="data">
                                    <thead>
                                      <tr>
                                        <th>Seq</th>
                                        <th>Fase</th>
                                        <th>Descrizione</th>
                                        <th>UM</th>
                                        <th>Note</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {fasi.map((fase) => (
                                        <tr key={`${key}-${fase.sequenza}`}>
                                          <td>{fase.sequenza}</td>
                                          <td>{fase.codice_fase}</td>
                                          <td>{fase.ds_fase || '—'}</td>
                                          <td>{fase.codice_unita_mis || '—'}</td>
                                          <td>{fase.note || '—'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </td>
                            </tr>
                          )}
                          {isUtilizziOpen && (
                            <tr className="cicli-row cicli-row--detail cicli-row--selected">
                              <td colSpan={9}>
                                {detailLoading === key ? (
                                  <div className="text-secondary">Caricamento utilizzi…</div>
                                ) : utilizzi.length === 0 ? (
                                  <div className="text-secondary">
                                    Nessun utilizzo nello storico per questo ciclo
                                    {storicoDisponibile
                                      ? ' (nel periodo disponibile).'
                                      : ' (tabelle storico non caricate).'}
                                  </div>
                                ) : (
                                  <table className="data">
                                    <thead>
                                      <tr>
                                        <th>Data bolla</th>
                                        <th>N. bolla</th>
                                        <th>Commessa</th>
                                        <th>Colore</th>
                                        <th>Modello</th>
                                        <th>Descrizione / Articolo</th>
                                        <th>Tessuto</th>
                                        <th>Art. fiscale</th>
                                        <th>Capi</th>
                                        <th>Kg</th>
                                        <th>Note</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {utilizzi.map((u, i) => (
                                        <tr
                                          key={`${key}-u-${u.anno_disposizione}-${u.nr_disposizione}-${u.riga_disposizione}-${i}`}
                                        >
                                          <td>{u.data_bolla || '—'}</td>
                                          <td>{u.nr_bolla || '—'}</td>
                                          <td>{u.commessa || '—'}</td>
                                          <td>{u.ds_colore || u.cd_colore || '—'}</td>
                                          <td>{u.modello || '—'}</td>
                                          <td>{u.ds_articolo || '—'}</td>
                                          <td>{u.tessuto || '—'}</td>
                                          <td>{u.articolo_fiscale || '—'}</td>
                                          <td>{u.capi_caricati ?? '—'}</td>
                                          <td>{u.kg_caricati ?? '—'}</td>
                                          <td>{u.note || '—'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                )}
                              </td>
                            </tr>
                          )}
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
                onPageChange={handlePageChange}
                label="Cicli"
              />
            </>
          )}
        </div>
      </div>
      </div>
    </>
  )
}

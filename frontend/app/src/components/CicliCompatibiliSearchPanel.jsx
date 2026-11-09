import React, { useCallback, useRef, useState } from 'react'
import CustomerAutocomplete from './CustomerAutocomplete'
import FilterSuggest from './FilterSuggest'
import FasiChipInput from './FasiChipInput'
import CicliCompatibiliResults from './CicliCompatibiliResults'
import LoadingOverlay from './LoadingOverlay'
import { authFetch } from '../utils/auth'
import { printCicliCompatibili } from '../utils/printReports'
import { LIVELLO_HINT } from './CicliCompatibiliResults'

const DEFAULT_LIVELLO = 4

const EMPTY_FILTERS = {
  codice_cliente: '',
  codice_ciclo: '',
  fasi: [],
  prezzi_presenti: false,
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

function cicloSelectionPayload(item) {
  return {
    codice_cliente: item.codice_cliente || '',
    codice_articolo: item.codice_articolo || '',
    codice_ciclo: item.codice_ciclo || '',
    codice_linea: item.codice_linea || '',
    codice_stagione: item.codice_stagione || '',
    codice_composizione: item.codice_composizione || '',
  }
}

/**
 * Vista «Ricerca cicli compatibili»: form (cliente / codice ciclo / fasi)
 * + eventuale selezione candidati + risultati con slider.
 */
export default function CicliCompatibiliSearchPanel() {
  const [filters, setFilters] = useState({ ...EMPTY_FILTERS })
  const [faseInput, setFaseInput] = useState('')
  const [livello, setLivello] = useState(DEFAULT_LIVELLO)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)
  const [needsSelection, setNeedsSelection] = useState(false)
  const [candidati, setCandidati] = useState([])
  const [selectedCiclo, setSelectedCiclo] = useState(null)
  const [compatibili, setCompatibili] = useState([])
  const [soglia, setSoglia] = useState(null)
  const [inputSummary, setInputSummary] = useState(null)

  const reqRef = useRef(0)
  const lastPayloadRef = useRef(null)

  const runSearch = useCallback(async (payload) => {
    const token = ++reqRef.current
    lastPayloadRef.current = payload
    setLoading(true)
    setError('')
    setSearched(true)

    try {
      const res = await authFetch('/api/cicli/compatibili', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (token !== reqRef.current) return

      if (!res.ok) {
        throw new Error(data.error || 'Errore ricerca cicli compatibili')
      }

      if (data.needs_selection) {
        setNeedsSelection(true)
        setCandidati(data.candidati || [])
        setSelectedCiclo(null)
        setCompatibili([])
        setInputSummary(null)
        setSoglia(data.soglia ?? null)
        return
      }

      setNeedsSelection(false)
      setCandidati([])
      setCompatibili(data.compatibili || [])
      setSoglia(data.soglia ?? null)
      setInputSummary(data.input || null)
      if (data.input && data.input_mode !== 'fasi') {
        setSelectedCiclo(cicloSelectionPayload(data.input))
      }
    } catch (err) {
      if (token !== reqRef.current) return
      console.error(err)
      setError(err.message || 'Errore ricerca')
      setNeedsSelection(false)
      setCandidati([])
      setCompatibili([])
      setInputSummary(null)
    } finally {
      if (token === reqRef.current) setLoading(false)
    }
  }, [])

  const buildPayloadFromFilters = (nextFilters, nextLivello, cicloOverride = null) => {
    const pending = faseInput.trim()
    let fasi = [...(nextFilters.fasi || [])]
    if (pending && !fasi.some((f) => f.toLowerCase() === pending.toLowerCase())) {
      fasi = [...fasi, pending]
    }
    const payload = {
      livello: nextLivello,
      prezzi_presenti: !!nextFilters.prezzi_presenti,
    }
    if (cicloOverride) {
      payload.ciclo = cicloOverride
      return { payload, fasi }
    }
    if (nextFilters.codice_cliente) payload.codice_cliente = nextFilters.codice_cliente
    if (nextFilters.codice_ciclo) payload.codice_ciclo = nextFilters.codice_ciclo
    if (fasi.length) payload.fasi = fasi
    return { payload, fasi }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFilters((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const { payload, fasi } = buildPayloadFromFilters(filters, livello)
    if (faseInput.trim() && fasi !== filters.fasi) {
      setFilters((prev) => ({ ...prev, fasi }))
      setFaseInput('')
    }

    if (!payload.ciclo && !payload.codice_ciclo && !(payload.fasi || []).length) {
      setError('Indicare un codice ciclo oppure una o più fasi.')
      setSearched(true)
      setNeedsSelection(false)
      setCandidati([])
      setCompatibili([])
      setInputSummary(null)
      setSelectedCiclo(null)
      return
    }
    if (!payload.ciclo && !payload.codice_ciclo && (payload.fasi || []).length && !payload.codice_cliente) {
      setError('Per la ricerca per sole fasi è obbligatorio il cliente.')
      setSearched(true)
      setNeedsSelection(false)
      setCandidati([])
      setCompatibili([])
      setInputSummary(null)
      setSelectedCiclo(null)
      return
    }

    setSelectedCiclo(null)
    runSearch(payload)
  }

  const handleReset = () => {
    reqRef.current += 1
    setFilters({ ...EMPTY_FILTERS })
    setFaseInput('')
    setLivello(DEFAULT_LIVELLO)
    setLoading(false)
    setError('')
    setSearched(false)
    setNeedsSelection(false)
    setCandidati([])
    setSelectedCiclo(null)
    setCompatibili([])
    setSoglia(null)
    setInputSummary(null)
    lastPayloadRef.current = null
  }

  const handleSelectCandidato = (item) => {
    const ciclo = cicloSelectionPayload(item)
    setSelectedCiclo(ciclo)
    const { payload } = buildPayloadFromFilters(filters, livello, ciclo)
    runSearch(payload)
  }

  const handleLivelloChange = (nextLivello) => {
    setLivello(nextLivello)
    if (!searched || needsSelection) return
    const base = lastPayloadRef.current
    if (!base) return
    const payload = { ...base, livello: nextLivello }
    if (selectedCiclo) payload.ciclo = selectedCiclo
    runSearch(payload)
  }

  const handlePrezziPresentiChange = (e) => {
    const checked = e.target.checked
    setFilters((prev) => ({ ...prev, prezzi_presenti: checked }))
    if (!searched || needsSelection) return
    const base = lastPayloadRef.current
    if (!base) return
    const payload = { ...base, prezzi_presenti: checked }
    if (selectedCiclo) payload.ciclo = selectedCiclo
    runSearch(payload)
  }

  return (
    <div className="cicli-compat-search">
      {loading && <LoadingOverlay />}

      <div className="panel">
        <div className="panel__head">Ricerca cicli compatibili</div>
        <div className="panel__body">
          <p className="field-hint" style={{ marginTop: 0, marginBottom: '1rem' }}>
            Cerca cicli simili a un codice ciclo (eventualmente scegliendo tra più match)
            oppure a una sequenza di fasi. Il cliente è opzionale con il codice ciclo;
            obbligatorio se cerchi solo per fasi.
          </p>

          <form onSubmit={handleSubmit} className="filters-form">
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
            </div>

            <div className="field field--full" style={{ marginBottom: '1rem' }}>
              <label>Fasi / lavorazioni</label>
              <FasiChipInput
                chips={filters.fasi}
                onChange={(fasi) => setFilters((prev) => ({ ...prev, fasi }))}
                draft={faseInput}
                onDraftChange={setFaseInput}
              />
            </div>

            <label className="checkbox-inline" style={{ marginBottom: '1rem' }}>
              <input
                type="checkbox"
                name="prezzi_presenti"
                checked={!!filters.prezzi_presenti}
                onChange={handlePrezziPresentiChange}
              />
              Solo cicli con offerta/prezzo &gt; 0
            </label>

            <div className="actions-bar">
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button type="submit" className="btn btn--primary" disabled={loading}>
                  Cerca compatibili
                </button>
                <button type="button" className="btn" onClick={handleReset} disabled={loading}>
                  Azzera
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {needsSelection && candidati.length > 0 ? (
        <div className="panel" style={{ marginTop: '1rem' }}>
          <div className="panel__head">
            Più cicli trovati — scegli il riferimento ({candidati.length})
          </div>
          <div className="panel__body">
            <div className="table-wrap">
              <table className="data chats-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Cod. ciclo</th>
                    <th>Articolo</th>
                    <th>Stagione</th>
                    <th>Linea</th>
                    <th>Composizione</th>
                    <th>Descrizione</th>
                    <th>Data</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {candidati.map((c) => (
                    <tr key={cicloKey(c)} className="chats-table__row">
                      <td>
                        <div>{c.ragione_sociale || c.codice_cliente}</div>
                        <div className="field-hint">{c.codice_cliente}</div>
                      </td>
                      <td>
                        <div>{c.codice_ciclo}</div>
                        {c.codice_ciclo_cli ? (
                          <div className="field-hint">{c.codice_ciclo_cli}</div>
                        ) : null}
                      </td>
                      <td>
                        <div>{c.codice_articolo}</div>
                        {c.ds_articolo ? (
                          <div className="field-hint">{c.ds_articolo}</div>
                        ) : null}
                      </td>
                      <td>{c.codice_stagione || c.ds_stagione || '—'}</td>
                      <td>{c.codice_linea || c.ds_linea || '—'}</td>
                      <td>{c.codice_composizione || c.ds_composizione || '—'}</td>
                      <td>{c.ds_ciclo || '—'}</td>
                      <td>{formatDateIso(c.data_ins)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--sm btn--primary"
                          onClick={() => handleSelectCandidato(c)}
                          disabled={loading}
                        >
                          Usa questo
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}

      {searched && !needsSelection ? (
        <div className="panel" style={{ marginTop: '1rem' }}>
          <div className="panel__head">
            <span>
              Risultati
              {inputSummary?.codice_ciclo
                ? ` · riferimento ${inputSummary.codice_ciclo}`
                : inputSummary?.fasi?.length
                  ? ` · fasi: ${inputSummary.fasi.join(', ')}`
                  : ''}
            </span>
            {compatibili.length > 0 && !loading && !error ? (
              <button
                type="button"
                className="btn btn--sm"
                title="Stampa i risultati con tutti i dettagli espansi"
                onClick={() => {
                  try {
                    printCicliCompatibili({
                      compatibili,
                      livello,
                      soglia,
                      livelloHint: LIVELLO_HINT,
                      inputSummary,
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
          </div>
          <div className="panel__body">
            <CicliCompatibiliResults
              loading={loading}
              error={error}
              compatibili={compatibili}
              livello={livello}
              soglia={soglia}
              onLivelloChange={handleLivelloChange}
            />
          </div>
        </div>
      ) : null}

      {searched && needsSelection && error ? (
        <div className="panel" style={{ marginTop: '1rem' }}>
          <div className="panel__body">
            <p className="pm-compat__error" style={{ margin: 0 }}>
              {error}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  )
}

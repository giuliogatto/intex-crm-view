import React, { useEffect, useRef, useState } from 'react'
import CustomerAutocomplete from './CustomerAutocomplete'
import LoadingOverlay from './LoadingOverlay'
import { authFetch } from '../utils/auth'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 15 * 1024 * 1024

const STAGES = [
  { after: 0, label: 'Invio immagine…' },
  { after: 2000, label: 'Estrazione testo dalla bolla (OCR)…' },
  { after: 25000, label: 'Ricerca cliente e cicli…' },
]

const EVIDENZA_LABELS = {
  codice_ciclo_manoscritto: 'Codice a mano',
  fasi: 'Fasi',
  commessa: 'Commessa',
  articolo: 'Articolo',
  descrizione: 'Descrizione',
  colore: 'Colore',
  composizione: 'Composizione',
}

const LIVELLO_LABELS = {
  alta: 'Confidenza alta',
  media: 'Confidenza media: verificare',
  bassa: 'Confidenza bassa: selezionare il cliente',
  nessuno: 'Mittente non letto: selezionare il cliente',
}

function cicloKey(c) {
  return [
    c.codice_cliente,
    c.codice_articolo,
    c.codice_ciclo,
    c.codice_linea,
    c.codice_stagione,
    c.codice_composizione,
  ].join('|')
}

function formatDateIso(iso) {
  if (!iso) return '—'
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!m) return iso
  return `${m[3]}/${m[2]}/${m[1]}`
}

function formatQty(riga) {
  const parts = []
  if (riga.quantita_capi != null) parts.push(`${riga.quantita_capi} capi`)
  if (riga.quantita_kg != null) parts.push(`${riga.quantita_kg} kg`)
  if (!parts.length) return null
  const um = riga.um ? ` (${riga.um})` : ''
  const fonte = riga.fonte_qty === 'manoscritta' ? ' · a mano' : ''
  return `${parts.join(' / ')}${um}${fonte}`
}

function ScoreBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const tone = pct >= 70 ? 'high' : pct >= 40 ? 'mid' : 'low'
  return (
    <div className={`bolla-score bolla-score--${tone}`} title={`Score ${pct}%`}>
      <div className="bolla-score__bar" style={{ width: `${pct}%` }} />
      <span className="bolla-score__label">{pct}%</span>
    </div>
  )
}

function RigaFields({ riga }) {
  const fields = [
    ['Articolo', riga.codice_articolo_cliente],
    ['Modello', riga.modello],
    ['Descrizione', riga.descrizione_articolo],
    ['Colore', riga.colore],
    ['Variante', riga.variante],
    ['Composizione', riga.composizione_testo],
    ['Commessa', riga.commessa],
    ['Stagione', riga.stagione],
    ['Tessuto', riga.tessuto],
    ['Quantità', formatQty(riga)],
    ['Fasi', riga.fasi_testo],
    ['Note', riga.note],
  ].filter(([, v]) => v)
  return (
    <dl className="bolla-fields">
      {fields.map(([label, value]) => (
        <div key={label} className="bolla-fields__item">
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export default function BollaUploadPanel({ onOpenInRicerca }) {
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [stage, setStage] = useState(STAGES[0].label)
  const [rematching, setRematching] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [codiceCliente, setCodiceCliente] = useState('')
  const [expandedKey, setExpandedKey] = useState(null)
  const [fasiByKey, setFasiByKey] = useState({})
  const [fasiLoading, setFasiLoading] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (!previewUrl) return undefined
    return () => URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  useEffect(() => {
    if (!loading) return undefined
    const timers = STAGES.map((s) => setTimeout(() => setStage(s.label), s.after))
    return () => timers.forEach(clearTimeout)
  }, [loading])

  const selectFile = (f) => {
    if (!f) return
    if (!ACCEPTED_TYPES.includes(f.type)) {
      setError('Formato non supportato: caricare JPEG, PNG o WEBP.')
      return
    }
    if (f.size > MAX_BYTES) {
      setError('Immagine troppo grande (max 15 MB).')
      return
    }
    setError(null)
    setResult(null)
    setCodiceCliente('')
    setExpandedKey(null)
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    selectFile(e.dataTransfer.files?.[0])
  }

  const applyResult = (data) => {
    setResult(data)
    setCodiceCliente(data.codice_cliente || '')
    setExpandedKey(null)
  }

  const analyze = async (force = false) => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      if (force) form.append('force', '1')
      const res = await authFetch('/api/cicli/ocr-bolla', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if (data.code === 'ocr_no_credits' || res.status === 402) {
          setError(
            data.error
            || 'Credito OpenAI esaurito: ricaricare il piano su platform.openai.com (Billing) e riprovare.'
          )
        } else {
          setError(data.error || `Errore server (${res.status})`)
        }
        return
      }
      applyResult(data)
    } catch (e) {
      console.error('Error OCR bolla:', e)
      setError('Impossibile contattare il server. Riprovare.')
    } finally {
      setLoading(false)
    }
  }

  const rematch = async (nextCliente) => {
    if (!result) return
    setCodiceCliente(nextCliente)
    setRematching(true)
    setError(null)
    try {
      const res = await authFetch('/api/cicli/ocr-bolla/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: result.session_id,
          ocr: result.ocr,
          codice_cliente: nextCliente || null,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(data.error || `Errore server (${res.status})`)
        return
      }
      applyResult({ ...result, ...data })
    } catch (e) {
      console.error('Error rematch bolla:', e)
      setError('Impossibile contattare il server. Riprovare.')
    } finally {
      setRematching(false)
    }
  }

  const reset = () => {
    setFile(null)
    setPreviewUrl(null)
    setResult(null)
    setError(null)
    setCodiceCliente('')
    setExpandedKey(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const toggleFasi = (c) => {
    const key = cicloKey(c)
    if (expandedKey === key) {
      setExpandedKey(null)
      return
    }
    setExpandedKey(key)
    if (fasiByKey[key]) return
    setFasiLoading(key)
    const params = new URLSearchParams({
      codice_cliente: c.codice_cliente,
      codice_articolo: c.codice_articolo,
      codice_ciclo: c.codice_ciclo,
      codice_linea: c.codice_linea,
      codice_stagione: c.codice_stagione,
      codice_composizione: c.codice_composizione,
    })
    authFetch(`/api/cicli/fasi?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => setFasiByKey((prev) => ({ ...prev, [key]: data.data || [] })))
      .catch((err) => {
        console.error('Error fetching fasi:', err)
        setFasiByKey((prev) => ({ ...prev, [key]: [] }))
      })
      .finally(() => setFasiLoading(null))
  }

  const ocr = result?.ocr
  const cliente = result?.cliente
  const righeMatch = new Map((result?.righe_match || []).map((r) => [r.riga, r]))

  return (
    <>
      {(loading || rematching) && <LoadingOverlay />}
      {loading && <div className="bolla-stage">{stage}</div>}

      <div className={`bolla-layout${previewUrl ? ' bolla-layout--with-preview' : ''}`}>
        <div className="bolla-main">
          <div className="panel">
            <div className="panel__head">
              <span>Upload bolla</span>
              {result && (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button type="button" className="btn btn--sm" onClick={() => analyze(true)}>
                    Rianalizza
                  </button>
                  <button type="button" className="btn btn--sm" onClick={reset}>
                    Nuova bolla
                  </button>
                </div>
              )}
            </div>
            <div className="panel__body">
              {!result && (
                <>
                  <div
                    className={`bolla-dropzone${dragOver ? ' bolla-dropzone--over' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragOver(true)
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
                    }}
                  >
                    <div className="bolla-dropzone__icon">📄</div>
                    <div className="bolla-dropzone__title">
                      {file ? file.name : 'Trascina qui la foto della bolla o clicca per selezionarla'}
                    </div>
                    <div className="text-secondary">
                      JPEG, PNG o WEBP, max 15 MB. Inquadrare tutta la bolla, ben illuminata e a fuoco.
                    </div>
                    <input
                      ref={inputRef}
                      type="file"
                      accept={ACCEPTED_TYPES.join(',')}
                      style={{ display: 'none' }}
                      onChange={(e) => selectFile(e.target.files?.[0])}
                    />
                  </div>
                  <div className="actions-bar" style={{ marginTop: '1rem' }}>
                    <button
                      type="button"
                      className="btn btn--primary"
                      disabled={!file || loading}
                      onClick={() => analyze(false)}
                    >
                      Analizza bolla
                    </button>
                  </div>
                </>
              )}
              {error && <div className="ddt-error-message" style={{ marginTop: '1rem' }}>⚠️ {error}</div>}

              {ocr && (
                <>
                  {(ocr.warnings || []).length > 0 && (
                    <div className="bolla-warnings">
                      {ocr.warnings.map((w) => (
                        <div key={w}>⚠️ {w}</div>
                      ))}
                    </div>
                  )}
                  <div className="filter-section-title">Documento</div>
                  <dl className="bolla-fields">
                    {[
                      ['Mittente', ocr.mittente_ragione_sociale],
                      ['Destinatario', ocr.destinatario_ragione_sociale],
                      ['N. bolla', ocr.numero_bolla],
                      ['Data', ocr.data_bolla ? formatDateIso(ocr.data_bolla) : null],
                      ['Causale', ocr.causale],
                      ['Cod. cliente su DDT', ocr.codice_cliente_su_ddt],
                      ['Rif. a mano', ocr.riferimento_interno_manoscritto],
                      ['Annotazioni a mano', (ocr.annotazioni_manoscritte || []).join(' · ')],
                      ['Note', ocr.note_documento],
                    ]
                      .filter(([, v]) => v)
                      .map(([label, value]) => (
                        <div key={label} className="bolla-fields__item">
                          <dt>{label}</dt>
                          <dd>{value}</dd>
                        </div>
                      ))}
                  </dl>
                  {(ocr.codice_ciclo_manoscritto || []).length > 0 && (
                    <div className="match-badges" style={{ marginBottom: '1rem' }}>
                      <span className="text-secondary" style={{ marginRight: '0.35rem' }}>
                        Codici ciclo a mano:
                      </span>
                      {ocr.codice_ciclo_manoscritto.map((c) => (
                        <span key={c} className="ddt-badge bolla-badge--code">
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="filter-section-title">Cliente</div>
                  <div className="bolla-cliente">
                    {cliente?.livello && (
                      <div className={`bolla-livello bolla-livello--${cliente.livello}`}>
                        {LIVELLO_LABELS[cliente.livello]}
                      </div>
                    )}
                    {(cliente?.candidati || []).length > 0 && (
                      <div className="bolla-cliente__candidati">
                        {cliente.candidati.map((c) => (
                          <button
                            key={c.codice_cliente}
                            type="button"
                            className={`bolla-cliente__option${
                              c.codice_cliente === codiceCliente ? ' bolla-cliente__option--selected' : ''
                            }`}
                            onClick={() => rematch(c.codice_cliente)}
                          >
                            <span>
                              {c.ragione_sociale}{' '}
                              <span className="text-secondary">({c.codice_cliente})</span>
                            </span>
                            <ScoreBar value={c.score} />
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="field" style={{ maxWidth: '420px' }}>
                      <label>Altro cliente</label>
                      <CustomerAutocomplete
                        value={codiceCliente}
                        onChange={(codice) => {
                          if (codice && codice !== codiceCliente) rematch(codice)
                        }}
                        placeholder="Cerca per nome o codice..."
                        endpoint="/api/cicli/clienti"
                      />
                    </div>
                  </div>

                  <div className="filter-section-title" style={{ marginTop: '1.25rem' }}>
                    Righe ({(ocr.righe || []).length})
                  </div>
                  {!codiceCliente && (
                    <div className="text-secondary" style={{ marginBottom: '1rem' }}>
                      Selezionare un cliente per cercare i cicli di lavorazione.
                    </div>
                  )}
                  {result.capabilities && !result.capabilities.cicli_search && (
                    <div className="text-secondary" style={{ marginBottom: '0.75rem' }}>
                      Indice ricerca fasi non popolato: matching fasi su descrizioni ciclo.
                    </div>
                  )}
                  {(ocr.righe || []).map((riga) => {
                    const match = righeMatch.get(riga.riga)
                    const candidati = match?.candidati_ciclo || []
                    return (
                      <div key={riga.riga} className="bolla-riga">
                        <div className="bolla-riga__head">
                          <strong>Riga {riga.riga}</strong>
                          {(match?.codici_cercati || riga.codice_ciclo_manoscritto || []).map((c) => (
                            <span key={c} className="ddt-badge bolla-badge--code">
                              {c}
                              {riga.codice_ciclo_ereditato ? ' (doc.)' : ''}
                            </span>
                          ))}
                        </div>
                        {riga.testo_grezzo && <div className="bolla-riga__raw">{riga.testo_grezzo}</div>}
                        <RigaFields riga={riga} />

                        {codiceCliente && candidati.length === 0 && (
                          <div className="text-secondary">Nessun ciclo candidato trovato per questa riga.</div>
                        )}
                        {candidati.length > 0 && (
                          <div className="table-wrap">
                            <table className="data">
                              <thead>
                                <tr>
                                  <th>Score</th>
                                  <th>Ciclo</th>
                                  <th>Descrizione</th>
                                  <th>Articolo</th>
                                  <th>Stagione</th>
                                  <th>Composizione</th>
                                  <th>Ultimo utilizzo</th>
                                  <th>Evidenze</th>
                                  <th></th>
                                </tr>
                              </thead>
                              <tbody>
                                {candidati.map((c) => {
                                  const key = cicloKey(c)
                                  const isOpen = expandedKey === key
                                  const fasi = fasiByKey[key] || []
                                  return (
                                    <React.Fragment key={key}>
                                      <tr>
                                        <td>
                                          <ScoreBar value={c.score} />
                                        </td>
                                        <td>
                                          <strong>{c.codice_ciclo}</strong>
                                          {c.codice_ciclo_cli ? (
                                            <div className="text-secondary">{c.codice_ciclo_cli}</div>
                                          ) : null}
                                        </td>
                                        <td>{c.ds_ciclo || '—'}</td>
                                        <td>
                                          {c.ds_articolo || c.codice_articolo}
                                          {c.ds_articolo ? (
                                            <div className="text-secondary">{c.codice_articolo}</div>
                                          ) : null}
                                        </td>
                                        <td>{c.ds_stagione || c.codice_stagione || '—'}</td>
                                        <td>{c.ds_composizione || c.codice_composizione || '—'}</td>
                                        <td>
                                          {formatDateIso(c.ultima_bolla)}
                                          {c.n_righe_storico ? (
                                            <div className="text-secondary">{c.n_righe_storico} righe</div>
                                          ) : null}
                                        </td>
                                        <td>
                                          <div className="match-badges" style={{ marginTop: 0 }}>
                                            {(c.evidenze || []).map((ev) => (
                                              <span
                                                key={ev}
                                                className={`ddt-badge${
                                                  ev === 'codice_ciclo_manoscritto' ? ' bolla-badge--code' : ''
                                                }`}
                                              >
                                                {EVIDENZA_LABELS[ev] || ev}
                                              </span>
                                            ))}
                                          </div>
                                        </td>
                                        <td style={{ whiteSpace: 'nowrap' }}>
                                          <span className="table-link" onClick={() => toggleFasi(c)}>
                                            {isOpen ? 'Nascondi fasi' : 'Fasi'}
                                          </span>
                                          {' · '}
                                          <span
                                            className="table-link"
                                            onClick={() =>
                                              onOpenInRicerca?.({
                                                codice_cliente: c.codice_cliente,
                                                codice_ciclo: c.codice_ciclo,
                                              })
                                            }
                                          >
                                            Apri in ricerca
                                          </span>
                                        </td>
                                      </tr>
                                      {isOpen && (
                                        <tr>
                                          <td colSpan={9}>
                                            {fasiLoading === key ? (
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
                                    </React.Fragment>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </>
              )}
            </div>
          </div>
        </div>

        {previewUrl && (
          <div className="bolla-preview panel">
            <div className="panel__head">Immagine</div>
            <div className="panel__body">
              <a href={previewUrl} target="_blank" rel="noreferrer">
                <img src={previewUrl} alt="Bolla caricata" />
              </a>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

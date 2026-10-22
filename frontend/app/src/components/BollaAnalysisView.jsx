import React, { useState } from 'react'
import CustomerAutocomplete from './CustomerAutocomplete'
import { authFetch } from '../utils/auth'

const EVIDENZA_LABELS = {
  codice_ciclo_manoscritto: 'Codice a mano',
  fasi: 'Fasi',
  commessa: 'Commessa',
  articolo: 'Articolo',
  tessuto: 'Tessuto',
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

/**
 * Vista completa del risultato OCR+match (stessa UI dell'analisi live).
 * @param {object} props
 * @param {object} props.ocr
 * @param {object} [props.cliente]
 * @param {array}  [props.righeMatch]
 * @param {string} [props.codiceCliente]
 * @param {object} [props.capabilities]
 * @param {boolean} [props.readOnly] — nasconde rematch / autocomplete
 * @param {function} [props.onSelectCliente]
 * @param {function} [props.onOpenInRicerca]
 */
export default function BollaAnalysisView({
  ocr,
  cliente,
  righeMatch = [],
  codiceCliente = '',
  capabilities,
  readOnly = false,
  onSelectCliente,
  onOpenInRicerca,
}) {
  const [expandedKey, setExpandedKey] = useState(null)
  const [fasiByKey, setFasiByKey] = useState({})
  const [fasiLoading, setFasiLoading] = useState(null)

  if (!ocr || typeof ocr !== 'object') {
    return <p className="users-empty">Nessun dato OCR disponibile per questa sessione.</p>
  }

  const matchByRiga = new Map((righeMatch || []).map((r) => [r.riga, r]))

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

  return (
    <div className="bolla-analysis-view">
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
            {cliente.candidati.map((c) => {
              const selected = c.codice_cliente === codiceCliente
              if (readOnly) {
                return (
                  <div
                    key={c.codice_cliente}
                    className={`bolla-cliente__option${selected ? ' bolla-cliente__option--selected' : ''}`}
                  >
                    <span>
                      {c.ragione_sociale}{' '}
                      <span className="text-secondary">({c.codice_cliente})</span>
                    </span>
                    <ScoreBar value={c.score} />
                  </div>
                )
              }
              return (
                <button
                  key={c.codice_cliente}
                  type="button"
                  className={`bolla-cliente__option${selected ? ' bolla-cliente__option--selected' : ''}`}
                  onClick={() => onSelectCliente?.(c.codice_cliente)}
                >
                  <span>
                    {c.ragione_sociale}{' '}
                    <span className="text-secondary">({c.codice_cliente})</span>
                  </span>
                  <ScoreBar value={c.score} />
                </button>
              )
            })}
          </div>
        )}
        {!readOnly && (
          <div className="field" style={{ maxWidth: '420px' }}>
            <label>Altro cliente</label>
            <CustomerAutocomplete
              value={codiceCliente}
              onChange={(codice) => {
                if (codice && codice !== codiceCliente) onSelectCliente?.(codice)
              }}
              placeholder="Cerca per nome o codice..."
              endpoint="/api/cicli/clienti"
            />
          </div>
        )}
        {readOnly && codiceCliente && !(cliente?.candidati || []).length && (
          <div className="text-secondary">Cliente scelto: {codiceCliente}</div>
        )}
      </div>

      <div className="filter-section-title" style={{ marginTop: '1.25rem' }}>
        Righe ({(ocr.righe || []).length})
      </div>
      {!codiceCliente && (
        <div className="text-secondary" style={{ marginBottom: '1rem' }}>
          {readOnly
            ? 'Nessun cliente selezionato: i cicli non sono stati cercati.'
            : 'Selezionare un cliente per cercare i cicli di lavorazione.'}
        </div>
      )}
      {capabilities && !capabilities.cicli_search && (
        <div className="text-secondary" style={{ marginBottom: '0.75rem' }}>
          Indice ricerca fasi non popolato: matching fasi su descrizioni ciclo.
        </div>
      )}

      {(ocr.righe || []).map((riga) => {
        const match = matchByRiga.get(riga.riga)
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
                              {onOpenInRicerca && (
                                <>
                                  {' · '}
                                  <span
                                    className="table-link"
                                    onClick={() =>
                                      onOpenInRicerca({
                                        codice_cliente: c.codice_cliente,
                                        codice_ciclo: c.codice_ciclo,
                                      })
                                    }
                                  >
                                    Apri in ricerca
                                  </span>
                                </>
                              )}
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
    </div>
  )
}

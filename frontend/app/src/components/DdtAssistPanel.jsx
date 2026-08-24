import React, { useState } from 'react'
import { authFetch } from '../utils/auth'
import CustomerAutocomplete from './CustomerAutocomplete'
import DateInput from './DateInput'
import LoadingOverlay from './LoadingOverlay'

export default function DdtAssistPanel() {
  const [codiceCliente, setCodiceCliente] = useState('')
  const [dataDdt, setDataDdt] = useState(() => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  })
  
  const [righe, setRighe] = useState([
    { id: 1, riga: 1, articolo: '', colore: '', quantita: 0 }
  ])
  
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const handleAddRiga = () => {
    setRighe(prev => {
      const nextRiga = prev.length > 0 ? Math.max(...prev.map(r => Number(r.riga) || 0)) + 1 : 1;
      return [...prev, { id: Date.now(), riga: nextRiga, articolo: '', colore: '', quantita: 0 }]
    });
  }
  
  const handleRemoveRiga = (id) => {
    setRighe(prev => prev.filter(r => r.id !== id))
  }
  
  const handleChangeRiga = (id, field, value) => {
    setRighe(prev => prev.map(r => r.id === id ? { ...r, [field]: value } : r))
  }

  const handleAvvia = async () => {
    if (!codiceCliente) {
      setError("Seleziona un cliente prima di avviare l'assistente.");
      return;
    }
    const righePopolate = righe.filter(r => r.articolo.trim() || r.colore.trim())
    if (righePopolate.length === 0) {
      setError("Inserisci almeno un articolo o colore in una riga prima di avviare.");
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const res = await authFetch('/api/ddt/assist/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          codice_cliente: codiceCliente,
          data_ddt: dataDdt,
          righe: righe.map(r => ({
            riga: r.riga,
            articolo: r.articolo.trim() || 'CAPI',
            colore: r.colore.trim() || '',
            quantita: Number(r.quantita)
          }))
        })
      });
      const data = await res.json();
      if (res.ok) {
        setResults(data.righe || []);
      } else {
        setError(data.error || "Errore dal server durante l'elaborazione del DDT.");
      }
    } catch (e) {
      console.error(e);
      setError("Impossibile connettersi al server. Verifica la tua connessione o riprova più tardi.");
    } finally {
      setLoading(false);
    }
  }

  const handleAccettaTutto = () => {
    // Mock action
    alert("Tutte le righe sono state accettate!");
  }

  const handleAccettaRiga = (rigaId) => {
    // Mock action
    alert(`Riga ${rigaId} accettata!`);
  }

  // Calcola stats aggregate sui campi corretti della risposta API
  const countSenzaStorico    = results ? results.filter(r => r.nessuno_storico === true).length : 0;
  const countComplete        = results ? results.filter(r => !r.nessuno_storico && r.cascata_usata === 'listino_cliente').length : 0;
  const countDaVerificare    = results ? results.filter(r => !r.nessuno_storico && r.cascata_usata !== 'listino_cliente').length : 0;

  return (
    <div className="ddt-assist-panel">
      {loading && <LoadingOverlay />}
      
      <div className="ddt-assist-header panel">
         <div className="panel__head">Configurazione Assistente DDT</div>
         <div className="panel__body ddt-assist-header__form">
            <div className="field" style={{ flex: 1, minWidth: '250px' }}>
              <label>Cliente</label>
              <CustomerAutocomplete
                name="codice_cliente"
                value={codiceCliente}
                onChange={(e) => setCodiceCliente(e.target.value)}
                placeholder="Cerca cliente per nome o codice..."
                allowClear
              />
            </div>
            <div className="field" style={{ minWidth: '150px' }}>
              <label>Data DDT</label>
              <DateInput
                name="data_ddt"
                value={dataDdt}
                onChange={(e) => setDataDdt(e.target.value)}
              />
            </div>
            <div className="ddt-assist-header__actions">
              <button className="btn btn--primary" onClick={handleAvvia}>Avvia Assistente</button>
            </div>
         </div>
         {error && (
           <div className="panel__body" style={{ paddingTop: 0 }}>
             <div className="ddt-error-message">
               ⚠️ {error}
             </div>
           </div>
         )}
      </div>

      <div className="ddt-assist-content">
        <div className="ddt-assist-input panel">
          <div className="panel__head">Righe DDT in ingresso</div>
          <div className="panel__body">
            <div className="table-wrap">
              <table className="data ddt-input-table">
                <thead>
                  <tr>
                    <th style={{width: '60px'}}>Riga</th>
                    <th>Articolo</th>
                    <th>Colore</th>
                    <th style={{width: '80px'}}>Q.tà</th>
                    <th style={{width: '40px'}}></th>
                  </tr>
                </thead>
                <tbody>
                  {righe.map(r => (
                    <tr key={r.id}>
                      <td>
                        <input type="number" value={r.riga} onChange={e => handleChangeRiga(r.id, 'riga', e.target.value)} className="ddt-inline-input" />
                      </td>
                      <td>
                        <input type="text" value={r.articolo} onChange={e => handleChangeRiga(r.id, 'articolo', e.target.value)} className="ddt-inline-input" placeholder="Es. T-Shirt" />
                      </td>
                      <td>
                        <input type="text" value={r.colore} onChange={e => handleChangeRiga(r.id, 'colore', e.target.value)} className="ddt-inline-input" placeholder="Es. Blu" />
                      </td>
                      <td>
                        <input type="number" value={r.quantita} onChange={e => handleChangeRiga(r.id, 'quantita', e.target.value)} className="ddt-inline-input" />
                      </td>
                      <td style={{textAlign: 'center'}}>
                        <button className="btn ddt-btn-icon" onClick={() => handleRemoveRiga(r.id)} title="Rimuovi riga">🗑️</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button className="btn" onClick={handleAddRiga} style={{marginTop: '1rem'}}>+ Aggiungi riga</button>
          </div>
        </div>

        <div className="ddt-assist-output panel">
          <div className="panel__head">Riconciliazione</div>
          <div className="panel__body" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {!results ? (
              <div className="ddt-empty-state">
                <div className="ddt-empty-icon">🤖</div>
                <p>Inserisci le righe e avvia l'assistente per vedere le proposte di riconciliazione basate sullo storico e listini.</p>
              </div>
            ) : results.length === 0 ? (
               <div className="ddt-empty-state">
                <div className="ddt-empty-icon">🤷</div>
                <p>Nessun risultato restituito dall'assistente.</p>
              </div>
            ) : (
              <div className="ddt-results-container">
                <div className="ddt-results-actions">
                  <button className="btn btn--primary" onClick={handleAccettaTutto}>Accetta tutto</button>
                </div>
                <div className="ddt-cards-list">
                  {results.map((res, i) => (
                    <DdtResultCard
                      key={i}
                      data={{
                        riga: res.riga?.riga ?? (i + 1),
                        articolo: res.riga?.articolo || '—',
                        colore: res.riga?.colore || '—',
                        proposte: res.proposte || [],
                        cascata: res.cascata_usata,
                        nessuno_storico: res.nessuno_storico,
                        confidenza: res.nessuno_storico ? 'nessuno_storico'
                          : res.cascata_usata === 'listino_cliente' ? 'alta' : 'media'
                      }}
                      onAccetta={() => handleAccettaRiga(res.riga?.riga ?? i + 1)}
                    />
                  ))}
                </div>
                <div className="ddt-assist-stats">
                  <span style={{ color: 'var(--success)' }}>🟢 {countComplete} complete</span>
                  <span style={{ color: 'var(--warning)' }}>🟡 {countDaVerificare} da verificare</span>
                  <span style={{ color: 'var(--text-muted)' }}>⚪ {countSenzaStorico} senza storico</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function DdtResultCard({ data, onAccetta }) {
  const confidenzaColor = () => {
    switch (data.confidenza?.toLowerCase()) {
      case 'alta': return 'green';
      case 'media': return 'yellow';
      case 'bassa': return 'red';
      default: return 'gray';
    }
  }

  const indicatorIcon = (conf) => {
    switch (conf?.toLowerCase()) {
      case 'alta': return '🟢';
      case 'media': return '🟡';
      case 'bassa': return '🔴';
      default: return '⚪';
    }
  }

  return (
    <div className={`ddt-result-card ddt-result-card--${confidenzaColor()}`}>
      <div className="ddt-result-card__header">
        <div className="ddt-result-card__title">
          <strong>Riga {data.riga}</strong> - {data.articolo} ({data.colore})
        </div>
        <span className="ddt-badge">{data.cascata || 'Nessuno storico'}</span>
      </div>
      <div className="ddt-result-card__body">
        {data.proposte && data.proposte.length > 0 ? (
          <div className="table-wrap">
            <table className="data ddt-proposte-table">
              <thead>
                <tr>
                  <th>Campo</th>
                  <th>Riferimento</th>
                  <th>Proposta</th>
                  <th>Fonte</th>
                  <th>Confidenza</th>
                </tr>
              </thead>
              <tbody>
                {data.proposte.map((p, j) => (
                  <tr key={j}>
                    <td>{p.campo}</td>
                    <td style={{color:'var(--text-muted)', fontSize:'0.85em'}}>{p.riferimento || '—'}</td>
                    <td><strong>
                      {p.valore_proposto !== undefined && p.valore_proposto !== null
                        ? (typeof p.valore_proposto === 'number'
                            ? p.valore_proposto.toLocaleString('it-IT', {minimumFractionDigits: 2, maximumFractionDigits: 4})
                            : p.valore_proposto)
                        : '—'}
                      {p.valore_descrizione ? <span style={{fontWeight:'normal', marginLeft:'0.4em', color:'var(--text-muted)'}}>({p.valore_descrizione})</span> : null}
                    </strong></td>
                    <td>{p.fonte}</td>
                    <td>
                      <span className={`ddt-conf-indicator ddt-conf-indicator--${p.confidenza?.toLowerCase()}`}>
                        {indicatorIcon(p.confidenza)} {p.confidenza}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="ddt-no-proposals">Nessuna proposta disponibile per questa riga.</p>
        )}
        <div className="ddt-result-card__actions">
           <button className="btn" onClick={() => alert('Riga rifiutata')}>Rifiuta</button>
           <button className="btn btn--primary" onClick={onAccetta}>Accetta</button>
        </div>
      </div>
    </div>
  )
}

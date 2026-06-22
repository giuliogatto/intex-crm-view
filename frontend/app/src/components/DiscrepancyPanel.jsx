import React, { useState, useEffect } from 'react'
import CustomerAutocomplete from './CustomerAutocomplete'
import { authFetch, downloadAuthFile } from '../utils/auth'

export default function DiscrepancyPanel({ selectedCustomer: customerProp, onCustomerChange }) {
  const [internalCustomer, setInternalCustomer] = useState('XXX')
  const selectedCustomer = customerProp ?? internalCustomer
  const setSelectedCustomer = onCustomerChange ?? setInternalCustomer
  const [discrepanze, setDiscrepanze] = useState([])
  const [loading, setLoading] = useState(false)

  // Fetch discrepancies on customer change
  useEffect(() => {
    if (!selectedCustomer) return
    setLoading(true)
    authFetch(`/api/discrepanze?codice_cliente=${selectedCustomer}`)
      .then((res) => res.json())
      .then((resData) => {
        if (resData.data) {
          setDiscrepanze(resData.data)
        }
        setLoading(false)
      })
      .catch((err) => {
        console.error('Error fetching discrepancies:', err)
        setLoading(false)
      })
  }, [selectedCustomer])

  const formatEuro = (num) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(num)
  }

  const exportCSV = () => {
    if (discrepanze.length === 0) return

    let csvContent = 'data:text/csv;charset=utf-8,'
    csvContent += 'Articolo,Colore,Capi Offerti,Valore Offerto,Capi Consegnati,Kg Consegnati,Valore Consegnato,Capi Fatturati,Kg Fatturati,Valore Fatturato,Diff Capi,Diff Valore\n'

    discrepanze.forEach((row) => {
      csvContent += `"${row.articolo_desc}","${row.colore}",${row.capi_offerti},${row.valore_offerto},${row.capi_consegnati},${row.kg_consegnati},${row.valore_consegnato},${row.capi_fatturati},${row.kg_fatturati},${row.valore_fatturato},${row.diff_capi},${row.diff_valore}\n`
    })

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `discrepanze_audit_${selectedCustomer}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const exportPDF = async () => {
    if (discrepanze.length === 0) return
    try {
      await downloadAuthFile(
        `/api/discrepanze/export/pdf?codice_cliente=${selectedCustomer}`,
        `discrepanze_audit_${selectedCustomer}.pdf`
      )
    } catch (err) {
      console.error('Error exporting PDF:', err)
    }
  }

  return (
    <div className="panel">
      <div className="panel__head">
        <span>Auditing Discrepanze (Offerta vs DDT vs Fattura)</span>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn" onClick={exportCSV} disabled={discrepanze.length === 0}>
            Esporta Report CSV
          </button>
          <button className="btn" onClick={exportPDF} disabled={discrepanze.length === 0}>
            Esporta Report PDF
          </button>
        </div>
      </div>
      <div className="panel__body">
        <div className="filters-grid" style={{ marginBottom: '2rem' }}>
          <div className="field">
            <label>Seleziona cliente da controllare</label>
            <CustomerAutocomplete
              value={selectedCustomer}
              onChange={setSelectedCustomer}
              placeholder="Cerca per nome o codice..."
            />
          </div>
        </div>

        {loading ? (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Analisi discrepanze in corso...</span>
          </div>
        ) : discrepanze.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">⚖️</div>
            <h3>Nessun dato di confronto</h3>
            <p>Non sono state trovate lavorazioni registrate per il cliente selezionato.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th rowspan="2">Articolo / Colore</th>
                  <th colspan="2" style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.02)' }}>Preventivato (Offerta)</th>
                  <th colspan="3" style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.04)' }}>Consegnato (DDT)</th>
                  <th colspan="3" style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.02)' }}>Fatturato (Fattura)</th>
                  <th colspan="2" style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.04)' }}>Differenze</th>
                </tr>
                <tr>
                  <th style={{ background: 'rgba(255, 255, 255, 0.02)' }}>Capi</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.02)' }}>Valore</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.04)' }}>Capi</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.04)' }}>Kg</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.04)' }}>Valore</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.02)' }}>Capi</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.02)' }}>Kg</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.02)' }}>Valore</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.04)' }}>Capi</th>
                  <th style={{ background: 'rgba(255, 255, 255, 0.04)' }}>Valore</th>
                </tr>
              </thead>
              <tbody>
                {discrepanze.map((row, idx) => {
                  const hasDiscrepancy = row.diff_capi !== 0 || row.diff_valore !== 0;
                  const rowClass = hasDiscrepancy ? 'discrepancy-row--warning' : '';

                  return (
                    <tr key={idx} className={rowClass}>
                      <td>
                        <strong>{row.articolo_desc}</strong>
                        <div className="text-secondary" style={{ fontSize: '0.8rem' }}>
                          {row.colore}
                        </div>
                      </td>
                      {/* Offer */}
                      <td style={{ background: 'rgba(255, 255, 255, 0.01)' }}>{row.capi_offerti || '—'}</td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.01)' }}>
                        {row.valore_offerto ? formatEuro(row.valore_offerto) : '—'}
                      </td>
                      {/* DDT */}
                      <td style={{ background: 'rgba(255, 255, 255, 0.02)' }}>{row.capi_consegnati || '—'}</td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.02)' }}>{row.kg_consegnati || '—'}</td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                        {row.valore_consegnato ? formatEuro(row.valore_consegnato) : '—'}
                      </td>
                      {/* Invoice */}
                      <td style={{ background: 'rgba(255, 255, 255, 0.01)' }}>{row.capi_fatturati || '—'}</td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.01)' }}>{row.kg_fatturati || '—'}</td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.01)' }}>
                        {row.valore_fatturato ? formatEuro(row.valore_fatturato) : '—'}
                      </td>
                      {/* Differences */}
                      <td style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                        {row.diff_capi === 0 ? (
                          <span className="text-secondary">—</span>
                        ) : (
                          <span className={`discrepancy-tag discrepancy-tag--${row.diff_capi > 0 ? 'pos' : 'neg'}`}>
                            {row.diff_capi > 0 ? `+${row.diff_capi}` : row.diff_capi}
                          </span>
                        )}
                      </td>
                      <td style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
                        {row.diff_valore === 0 ? (
                          <span className="text-secondary">—</span>
                        ) : (
                          <span className={`discrepancy-tag discrepancy-tag--${row.diff_valore > 0 ? 'pos' : 'neg'}`}>
                            {row.diff_valore > 0 ? `+${formatEuro(row.diff_valore)}` : formatEuro(row.diff_valore)}
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

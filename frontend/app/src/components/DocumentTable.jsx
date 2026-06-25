import React from 'react'

export default function DocumentTable({ activeTab, data, totals, onViewDetail, onViewBollaDetail, onViewOffertaDetail }) {
  const formatEuro = (num) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(num)
  }

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📂</div>
        <h3>Nessun documento trovato</h3>
        <p>Prova a modificare i filtri di ricerca o ad inserire un valore differente.</p>
      </div>
    )
  }

  return (
    <div className="table-wrap">
      {activeTab === 'bolle' && (
        <table className="data">
          <thead>
            <tr>
              <th>N. bolla</th>
              <th>Data</th>
              <th>Cliente</th>
              <th>Righe collegate</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <tr key={item.numero_bolla}>
                <td><strong>{item.numero_bolla}</strong></td>
                <td>{item.data}</td>
                <td>
                  {item.cliente} <span className="text-secondary">({item.codice_cliente})</span>
                </td>
                <td>{item.righe_collegate}</td>
                <td>
                  <span
                    className="table-link"
                    onClick={() => onViewBollaDetail(item.numero_bolla)}
                  >
                    Righe
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {activeTab === 'fatture' && (
        <table className="data">
          <thead>
            <tr>
              <th>N. disp.</th>
              <th>Periodo riferimento</th>
              <th>Cliente</th>
              <th>Importo documento</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <tr key={`${item.codice_cliente}-${item.numero_disposizione}`}>
                <td><strong>{item.numero_disposizione}</strong></td>
                <td>{item.data}</td>
                <td>
                  {item.cliente} <span className="text-secondary">({item.codice_cliente})</span>
                </td>
                <td>{formatEuro(item.importo_documento)}</td>
                <td>
                  <span
                    className="table-link"
                    onClick={() => onViewDetail(item.numero_disposizione, item.codice_cliente)}
                  >
                    Dettaglio
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          {totals?.importo_documento != null && (
            <tfoot>
              <tr className="table-totals-row">
                <td colSpan={3}><strong>Totale</strong></td>
                <td><strong>{formatEuro(totals.importo_documento)}</strong></td>
                <td></td>
              </tr>
            </tfoot>
          )}
        </table>
      )}

      {activeTab === 'offerte' && (
        <table className="data">
          <thead>
            <tr>
              <th>N. offerta</th>
              <th>Data</th>
              <th>Cliente</th>
              <th>Stagione</th>
              <th>Importo</th>
              <th>Stato</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.map((item) => (
              <tr key={item.numero_offerta}>
                <td><strong>{item.numero_offerta}</strong></td>
                <td>{item.data}</td>
                <td>
                  {item.cliente} <span className="text-secondary">({item.codice_cliente})</span>
                </td>
                <td>{item.stagione}</td>
                <td>{formatEuro(item.importo)}</td>
                <td>
                  <span className={`pill pill--${(item.stato ?? '').toLowerCase()}`}>
                    {item.stato ?? '—'}
                  </span>
                </td>
                <td>
                  <span
                    className="table-link"
                    onClick={() => onViewOffertaDetail(item.numero_offerta)}
                  >
                    Dettaglio
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          {totals?.importo != null && (
            <tfoot>
              <tr className="table-totals-row">
                <td colSpan={4}><strong>Totale</strong></td>
                <td><strong>{formatEuro(totals.importo)}</strong></td>
                <td colSpan={2}></td>
              </tr>
            </tfoot>
          )}
        </table>
      )}
    </div>
  )
}

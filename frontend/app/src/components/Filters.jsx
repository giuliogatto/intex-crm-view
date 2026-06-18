import React, { useState, useEffect } from 'react'
import DateInput from './DateInput'
import CustomerAutocomplete from './CustomerAutocomplete'

export default function Filters({ activeTab, onSearch, onExport }) {
  const [filters, setFilters] = useState({
    data_inizio: '',
    data_fine: '',
    codice_cliente: '',
    stagione: '',
    stato: 'Tutte'
  })

  // Reset status value when activeTab changes
  useEffect(() => {
    setFilters(prev => ({
      ...prev,
      stato: activeTab === 'offerte' ? 'Tutti' : 'Tutte'
    }))
  }, [activeTab])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFilters((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSearch(filters)
  }

  const handleReset = () => {
    const cleared = {
      data_inizio: '',
      data_fine: '',
      codice_cliente: '',
      stagione: '',
      stato: activeTab === 'offerte' ? 'Tutti' : 'Tutte'
    }
    setFilters(cleared)
    onSearch(cleared)
  }

  return (
    <form onSubmit={handleSubmit} className="filters-form">
      <div className="filters-grid">
        <div className="field">
          <label>Data da</label>
          <DateInput
            name="data_inizio"
            value={filters.data_inizio}
            onChange={handleChange}
            placeholder="Seleziona data inizio"
          />
        </div>
        <div className="field">
          <label>Data a</label>
          <DateInput
            name="data_fine"
            value={filters.data_fine}
            onChange={handleChange}
            placeholder="Seleziona data fine"
          />
        </div>
        <div className="field">
          <label>Cliente</label>
          <CustomerAutocomplete
            name="codice_cliente"
            value={filters.codice_cliente}
            onChange={handleChange}
            placeholder="Cerca per nome o codice..."
            allowClear
          />
        </div>
        <div className="field">
          <label>Stagione</label>
          <input
            type="text"
            name="stagione"
            value={filters.stagione}
            onChange={handleChange}
            placeholder="E.g. PE2026"
          />
        </div>

        {activeTab === 'fatture' && (
          <div className="field">
            <label>Stato pagamento</label>
            <select name="stato" value={filters.stato} onChange={handleChange}>
              <option value="Tutte">Tutte</option>
              <option value="Pagata">Pagate</option>
              <option value="Aperta">Aperte</option>
            </select>
          </div>
        )}

        {activeTab === 'offerte' && (
          <div className="field">
            <label>Stato trattativa</label>
            <select name="stato" value={filters.stato} onChange={handleChange}>
              <option value="Tutti">Tutti</option>
              <option value="Accettata">Accettate</option>
              <option value="Aperta">Aperte</option>
              <option value="Rifiutata">Rifiutate</option>
            </select>
          </div>
        )}
      </div>

      <div className="actions-bar">
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button type="submit" className="btn btn--primary">
            Cerca
          </button>
          <button type="button" onClick={handleReset} className="btn">
            Azzera filtri
          </button>
        </div>
        <div>
          <button type="button" onClick={onExport} className="btn">
            Esporta CSV
          </button>
        </div>
      </div>
    </form>
  )
}
